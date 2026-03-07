"""Async auth helpers for Ecobee Air Quality integration."""

from __future__ import annotations

import base64
import hashlib
import logging
import re
import secrets
from urllib.parse import parse_qs, urlparse

import aiohttp

from .const import (
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_DOMAIN,
    AUTH0_REDIRECT,
    AUTH0_SCOPES,
)

_LOGGER = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication fails."""


class MFARequired(Exception):
    """Raised when MFA verification is needed.

    The caller must collect the OTP and call EcobeeAuth.async_submit_mfa().
    """

    def __init__(self, message: str = "MFA code required"):
        super().__init__(message)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE verifier and challenge."""
    verifier = secrets.token_urlsafe(32)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def extract_code_from_url(url: str) -> str | None:
    """Extract the authorization code from a callback URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        codes = params.get("code", [])
        return codes[0] if codes else None
    except Exception:
        return None


def _extract_form_state(html: str) -> str:
    """Extract the Auth0 state parameter from a login page."""
    match = re.search(
        r'name="state"\s+[^>]*value="([^"]+)"', html
    ) or re.search(r'name="state"\s+value="([^"]+)"', html)
    if not match:
        raise AuthError("Could not parse Auth0 login page")
    return match.group(1)


class EcobeeAuth:
    """Manages the multi-step Auth0 Universal Login flow.

    Auth0 New Universal Login uses form-based identifier-first flow:
    1. GET /authorize → redirects to /u/login/identifier
    2. POST /u/login/identifier (email) → redirects to /u/login/password
    3. POST /u/login/password (password) → redirects to callback with code
       OR redirects to /u/mfa-otp-challenge if MFA is enabled
    4. POST /u/mfa-otp-challenge (OTP) → redirects to callback with code
    5. Exchange code for tokens via PKCE
    """

    def __init__(self) -> None:
        self._verifier: str | None = None
        self._jar: aiohttp.CookieJar | None = None
        self._mfa_state: str | None = None
        self._mfa_url: str | None = None

    async def async_login(
        self, email: str, password: str
    ) -> tuple[str, str | None]:
        """Start the login flow.

        Returns (access_token, refresh_token) on success.
        Raises MFARequired if MFA is needed (call async_submit_mfa next).
        Raises AuthError on failure.
        """
        self._verifier, challenge = generate_pkce_pair()
        # unsafe=True allows cookies across Auth0 subdomains during login
        self._jar = aiohttp.CookieJar(unsafe=True)
        return await self._do_login(email, password, challenge)

    async def _do_login(
        self, email: str, password: str, challenge: str
    ) -> tuple[str, str | None]:
        """Internal login implementation."""
        async with aiohttp.ClientSession(cookie_jar=self._jar) as session:
            # Step 1: GET /authorize → login identifier page
            async with session.get(
                f"https://{AUTH0_DOMAIN}/authorize",
                params={
                    "client_id": AUTH0_CLIENT_ID,
                    "response_type": "code",
                    "redirect_uri": AUTH0_REDIRECT,
                    "audience": AUTH0_AUDIENCE,
                    "scope": AUTH0_SCOPES,
                    "prompt": "login",
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "state": secrets.token_urlsafe(16),
                },
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    raise AuthError(
                        f"Failed to load login page (HTTP {resp.status})"
                    )
                identifier_html = await resp.text()
                identifier_url = str(resp.url).split("?")[0]

            login_state = _extract_form_state(identifier_html)

            # Step 2: POST email to /u/login/identifier
            async with session.post(
                identifier_url,
                data={
                    "state": login_state,
                    "username": email,
                    "js-available": "true",
                    "webauthn-available": "false",
                    "is-brave": "false",
                    "webauthn-platform-available": "false",
                    "action": "default",
                },
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    raise AuthError(
                        f"Identifier step failed (HTTP {resp.status})"
                    )
                password_html = await resp.text()
                password_url = str(resp.url).split("?")[0]

            if "/u/login/password" not in password_url:
                # Check for error message in the page
                error_match = re.search(
                    r'class="[^"]*error[^"]*"[^>]*>([^<]+)', password_html
                )
                if error_match:
                    raise AuthError(error_match.group(1).strip())
                raise AuthError("Unexpected page after email submission")

            password_state = _extract_form_state(password_html)

            # Step 3: POST password to /u/login/password
            # Don't follow redirects — we need to intercept the auth code
            # before ecobee.com's callback page consumes it
            async with session.post(
                password_url,
                data={
                    "state": password_state,
                    "username": email,
                    "password": password,
                    "action": "default",
                },
                allow_redirects=False,
            ) as resp:
                # Wrong password returns 400 staying on password page
                if resp.status in (200, 400):
                    raise AuthError("Invalid email or password")

                if resp.status not in (302, 301):
                    raise AuthError(
                        f"Password step unexpected status: {resp.status}"
                    )
                location = resp.headers.get("Location", "")

            # Follow redirects manually to find code or MFA page
            # We need to stop at auth code and not follow to ecobee.com
            for _ in range(10):
                # Resolve relative URLs
                if location.startswith("/"):
                    location = f"https://{AUTH0_DOMAIN}{location}"

                code = extract_code_from_url(location)
                if code:
                    return await self._exchange_code(session, code)

                # Check if redirect is to MFA page
                if "/u/mfa" in location:
                    async with session.get(
                        location, allow_redirects=True
                    ) as mfa_resp:
                        mfa_html = await mfa_resp.text()
                        self._mfa_url = str(mfa_resp.url).split("?")[0]
                        self._mfa_state = _extract_form_state(mfa_html)
                    raise MFARequired()

                # Follow redirect
                async with session.get(
                    location, allow_redirects=False
                ) as resp:
                    if resp.status in (302, 301):
                        location = resp.headers.get("Location", "")
                    else:
                        raise AuthError(
                            f"Unexpected status {resp.status} at {location[:100]}"
                        )

            raise AuthError("Too many redirects during login")

    async def async_submit_mfa(self, otp_code: str) -> tuple[str, str | None]:
        """Submit MFA OTP code and complete login.

        Must be called after async_login raises MFARequired.
        Returns (access_token, refresh_token).
        """
        if not self._jar or not self._mfa_state or not self._mfa_url:
            raise AuthError("No MFA session. Call async_login first.")

        async with aiohttp.ClientSession(cookie_jar=self._jar) as session:
            # Use allow_redirects=False to intercept the auth code
            # before ecobee.com's callback page consumes it
            async with session.post(
                self._mfa_url,
                data={
                    "state": self._mfa_state,
                    "code": otp_code,
                    "action": "default",
                },
                allow_redirects=False,
            ) as resp:
                # Wrong code returns 400 staying on MFA page
                if resp.status in (200, 400):
                    raise AuthError("Invalid verification code")

                if resp.status not in (302, 301):
                    raise AuthError(
                        f"MFA step unexpected status: {resp.status}"
                    )
                location = resp.headers.get("Location", "")

            # Follow redirects manually, stopping when we find the code
            return await self._follow_redirects_for_code(session, location)

    async def _follow_redirects_for_code(
        self, session: aiohttp.ClientSession, location: str
    ) -> tuple[str, str | None]:
        """Follow redirect chain, extracting auth code before ecobee.com gets it."""
        for _ in range(10):
            # Resolve relative URLs
            if location.startswith("/"):
                location = f"https://{AUTH0_DOMAIN}{location}"

            code = extract_code_from_url(location)
            if code:
                return await self._exchange_code(session, code)

            # Follow this redirect
            async with session.get(
                location, allow_redirects=False
            ) as resp:
                if resp.status in (302, 301):
                    location = resp.headers.get("Location", "")
                else:
                    raise AuthError(
                        f"Unexpected status {resp.status} during redirect chain"
                    )

        raise AuthError("Too many redirects after MFA")

    async def _exchange_code(
        self, session: aiohttp.ClientSession, code: str
    ) -> tuple[str, str | None]:
        """Exchange auth code for tokens via PKCE."""
        async with session.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": AUTH0_CLIENT_ID,
                "code": code,
                "redirect_uri": AUTH0_REDIRECT,
                "code_verifier": self._verifier,
            },
        ) as resp:
            if resp.status != 200:
                raise AuthError(
                    f"Token exchange failed (HTTP {resp.status})"
                )
            data = await resp.json()

        access_token = data.get("access_token")
        if not access_token:
            raise AuthError("No access_token in token response")

        _LOGGER.info("Successfully obtained ecobee tokens via login flow")
        return access_token, data.get("refresh_token")


async def async_refresh_token(
    session: aiohttp.ClientSession, refresh_token: str
) -> tuple[str, str, int]:
    """Refresh an access token using a refresh token.

    Returns (access_token, refresh_token, expires_in).
    Raises AuthError on failure.
    """
    async with session.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": AUTH0_CLIENT_ID,
            "refresh_token": refresh_token,
        },
    ) as resp:
        if resp.status != 200:
            raise AuthError(
                f"Token refresh failed (HTTP {resp.status})"
            )
        data = await resp.json()

    access_token = data.get("access_token")
    if not access_token:
        raise AuthError("No access_token in refresh response")

    new_refresh = data.get("refresh_token", refresh_token)
    expires_in = data.get("expires_in", 3600)
    return access_token, new_refresh, expires_in
