"""Constants for Ecobee Air Quality integration."""

from datetime import timedelta

DOMAIN = "ecobee_air_quality"

# Auth0 config (from ecobee web app)
AUTH0_DOMAIN = "auth.ecobee.com"
AUTH0_CLIENT_ID = "183eORFPlXyz9BbDZwqexHPBQoVjgadh"
AUTH0_AUDIENCE = "https://prod.ecobee.com/api/v1"
AUTH0_REDIRECT = "https://www.ecobee.com/home/authCallback"
AUTH0_SCOPES = "openid smartRead offline_access"

# API
ECOBEE_API = "https://api.ecobee.com/1/thermostat"

# Polling
SCAN_INTERVAL = timedelta(minutes=5)

# Sensor definitions: (key, name_suffix, device_class, unit, icon)
SENSOR_TYPES = {
    "co2": {
        "name": "CO2",
        "device_class": "carbon_dioxide",
        "native_unit_of_measurement": "ppm",
        "state_class": "measurement",
        "icon": "mdi:molecule-co2",
        "data_key": "co2_ppm",
    },
    "voc": {
        "name": "VOC",
        "device_class": "volatile_organic_compounds_parts",
        "native_unit_of_measurement": "ppb",
        "state_class": "measurement",
        "icon": "mdi:air-filter",
        "data_key": "voc_ppb",
    },
    "air_quality_score": {
        "name": "Air Quality Score",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:leaf",
        "data_key": "aq_score",
    },
    "equipment_status": {
        "name": "Equipment Status",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:hvac",
        "data_key": "equipment_status",
    },
    "cool_stages": {
        "name": "Cooling Stages",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:snowflake",
        "data_key": "cool_stages",
    },
    "heat_stages": {
        "name": "Heating Stages",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:fire",
        "data_key": "heat_stages",
    },
}
