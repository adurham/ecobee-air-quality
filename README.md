# Ecobee Air Quality

A Home Assistant custom integration that exposes CO2, VOC, and Air Quality Score sensors from ecobee thermostats with built-in air quality monitoring.

## Sensors

For each thermostat with an air quality sensor, this integration creates:

| Sensor | Unit | Device Class |
|--------|------|-------------|
| CO2 | ppm | `carbon_dioxide` |
| VOC | ppb | `volatile_organic_compounds_parts` |
| Air Quality Score | — | — |

Sensors poll every 5 minutes. Thermostats without air quality hardware are automatically excluded.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/adurham/ecobee-air-quality` as an **Integration**
4. Search for "Ecobee Air Quality" and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/ecobee_air_quality` folder into your Home Assistant `custom_components` directory and restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Ecobee Air Quality**
3. Enter your ecobee account email and password
4. If MFA is enabled, enter your verification code when prompted
5. Sensors will appear under the **Ecobee [Thermostat Name]** device

Your credentials are used once to obtain a refresh token and are never stored. The refresh token is used for ongoing API access and is automatically rotated.

### Advanced: Manual refresh token

If the login flow doesn't work for your account, you can paste a refresh token directly in the setup form. Obtain one from ecobee's Auth0 token endpoint using the PKCE flow with client ID `183eORFPlXyz9BbDZwqexHPBQoVjgadh`.

## Reauth

If the refresh token expires or is revoked, Home Assistant will show a notification prompting you to re-authenticate. The reauth flow is the same as initial setup.

## Known Limitations

- **Unofficial API** — This integration uses ecobee's consumer API, not an official developer API. Ecobee could change or restrict it at any time.
- **Token lifetime** — Refresh token durability depends on ecobee's Auth0 server-side configuration (e.g., absolute expiry, inactivity timeout), which we don't control. If the token expires, Home Assistant will prompt you to re-authenticate. How frequently this happens (if ever) is unknown.
- **Token rotation** — Auth0 may rotate refresh tokens on each use. If Home Assistant crashes between receiving a new token and persisting it, the old token may be invalidated. In practice Auth0 provides a short reuse window, making this unlikely but possible.

## How it works

Ecobee's consumer API (the same one the web app uses) returns air quality data that isn't available through ecobee's official developer API. This integration authenticates via ecobee's Auth0 login flow with PKCE, then polls the consumer API for thermostat data including CO2, VOC, and air quality score readings.

## License

MIT
