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

# Polling — ecobee API docs say "DO NOT poll at an interval quicker than
# once every 3 minutes, which is the shortest interval at which data might
# change." We use the minimum allowed (3 min) for the best stage-transition
# resolution on compressor_cool_stage / runtime_seconds sensors.
SCAN_INTERVAL = timedelta(minutes=3)

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
    # Parsed from the equipmentStatus CSV string (e.g. "compCool1,fan").
    # These give live compressor staging — the real signal for "is stage 2
    # engaged right now?" — unlike cool_stages/heat_stages which read the
    # static settings.coolStages/heatStages config (unit capability, not
    # live state). Values: 0=idle, 1=stage1, 2=stage2.
    "compressor_cool_stage": {
        "name": "Compressor Cool Stage",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:snowflake",
        "data_key": "compressor_cool_stage",
    },
    "compressor_heat_stage": {
        "name": "Compressor Heat Stage",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:fire",
        "data_key": "compressor_heat_stage",
    },
    "fan_running": {
        "name": "Fan Running",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": "measurement",
        "icon": "mdi:fan",
        "data_key": "fan_running",
    },
    # Per-stage runtime seconds from extendedRuntime (last 5-min interval).
    # Each value is 0-300 seconds. These are the REAL stage history —
    # how long each equipment actually ran in the most recent 5-min window.
    # Use these to compute stage duty cycle, aux heat usage (expensive!),
    # dehumidifier runtime, etc.
    "cool1_runtime_seconds": {
        "name": "Cool Stage 1 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:snowflake",
        "data_key": "cool1_runtime_seconds",
    },
    "cool2_runtime_seconds": {
        "name": "Cool Stage 2 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:snowflake-alert",
        "data_key": "cool2_runtime_seconds",
    },
    "aux_heat1_runtime_seconds": {
        "name": "Aux Heat 1 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fire",
        "data_key": "aux_heat1_runtime_seconds",
    },
    "aux_heat2_runtime_seconds": {
        "name": "Aux Heat 2 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fire",
        "data_key": "aux_heat2_runtime_seconds",
    },
    "aux_heat3_runtime_seconds": {
        "name": "Aux Heat 3 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fire",
        "data_key": "aux_heat3_runtime_seconds",
    },
    "heat_pump1_runtime_seconds": {
        "name": "Heat Pump Stage 1 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:heat-pump",
        "data_key": "heat_pump1_runtime_seconds",
    },
    "heat_pump2_runtime_seconds": {
        "name": "Heat Pump Stage 2 Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:heat-pump",
        "data_key": "heat_pump2_runtime_seconds",
    },
    "fan_runtime_seconds": {
        "name": "Fan Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fan",
        "data_key": "fan_runtime_seconds",
    },
    "dehumidifier_runtime_seconds": {
        "name": "Dehumidifier Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:water-off",
        "data_key": "dehumidifier_runtime_seconds",
    },
    "humidifier_runtime_seconds": {
        "name": "Humidifier Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:water",
        "data_key": "humidifier_runtime_seconds",
    },
    "ventilator_runtime_seconds": {
        "name": "Ventilator Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:air-conditioner",
        "data_key": "ventilator_runtime_seconds",
    },
    "economizer_runtime_seconds": {
        "name": "Economizer Runtime",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:leaf",
        "data_key": "economizer_runtime_seconds",
    },
    # Dehumidify overcool offset (tenths of a degree F) from extendedRuntime.
    # When the AC is overcooling for dehumidification, this shows how many
    # tenths of a degree below the setpoint it's targeting. 0 = no overcool.
    # NO device_class: this is a DELTA (°F below setpoint), not an absolute
    # temperature. Setting device_class: temperature makes the HA Prometheus
    # exporter convert °F→°C using the absolute formula (F-32)*5/9, which is
    # wrong for a delta. Using a custom unit avoids the auto-conversion.
    "dehumidify_overcool_offset": {
        "name": "Dehumidify Overcool Offset",
        "device_class": None,
        "native_unit_of_measurement": "°F-delta",
        "state_class": "measurement",
        "icon": "mdi:thermometer-low",
        "data_key": "dehumidify_overcool_offset",
    },
    # Live dehumidify target (%) from runtime — the RH the AC is trying to
    # hold by overcooling. Different from the static settings.dehumidifierLevel
    # because it can change with comfort settings (Home/Away/Sleep).
    "desired_dehumidity": {
        "name": "Desired Dehumidity",
        "device_class": "humidity",
        "native_unit_of_measurement": "%",
        "state_class": "measurement",
        "icon": "mdi:water-percent-outline",
        "data_key": "desired_dehumidity",
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
    "humidity": {
        "name": "Humidity",
        "device_class": "humidity",
        "native_unit_of_measurement": "%",
        "state_class": "measurement",
        "icon": "mdi:water-percent",
        "data_key": "humidity",
    },
}
