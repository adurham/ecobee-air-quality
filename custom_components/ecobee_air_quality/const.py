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
    # ---- Staging thresholds (from settings block) ----
    # ecobee exposes ONLY stage1* thresholds. There is NO stage2 differential
    # key in the API — stage-2 engagement is an internal ecobee algorithm not
    # readable via the consumer API. The live stage signal is the
    # compressor_cool_stage sensor above. These thresholds tell you WHEN
    # stage 1 starts and the min compressor runtime, but not when stage 2
    # engages. Values are converted from ecobee's tenths-of-F to degrees F.
    "stage1_cooling_differential_temp_f": {
        "name": "Stage 1 Cooling Differential Temp",
        "device_class": None,
        "native_unit_of_measurement": "°F-delta",
        "state_class": "measurement",
        "icon": "mdi:thermometer-chevron-up",
        "data_key": "stage1_cooling_differential_temp_f",
    },
    "stage1_heating_differential_temp_f": {
        "name": "Stage 1 Heating Differential Temp",
        "device_class": None,
        "native_unit_of_measurement": "°F-delta",
        "state_class": "measurement",
        "icon": "mdi:thermometer-chevron-down",
        "data_key": "stage1_heating_differential_temp_f",
    },
    # Cool dissipation time = fan aftercycle (seconds the fan keeps running
    # after cooling turns off) — NOT a stage-2 timer, despite the name.
    "stage1_cooling_dissipation_time_s": {
        "name": "Stage 1 Cooling Dissipation Time",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fan-clock",
        "data_key": "stage1_cooling_dissipation_time_s",
    },
    "stage1_heating_dissipation_time_s": {
        "name": "Stage 1 Heating Dissipation Time",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:fan-clock",
        "data_key": "stage1_heating_dissipation_time_s",
    },
    "compressor_protection_min_time_s": {
        "name": "Compressor Protection Min Time",
        "device_class": "duration",
        "native_unit_of_measurement": "s",
        "state_class": "measurement",
        "icon": "mdi:shield-alert-outline",
        "data_key": "compressor_protection_min_time_s",
    },
    "compressor_protection_min_temp_f": {
        "name": "Compressor Protection Min Temp",
        "device_class": None,
        "native_unit_of_measurement": "°F",
        "state_class": "measurement",
        "icon": "mdi:snowflake-thermometer",
        "data_key": "compressor_protection_min_temp_f",
    },
    "heat_cool_min_delta_f": {
        "name": "Heat Cool Min Delta",
        "device_class": None,
        "native_unit_of_measurement": "°F-delta",
        "state_class": "measurement",
        "icon": "mdi:arrow-split-horizontal",
        "data_key": "heat_cool_min_delta_f",
    },
    # Setpoint ranges (the envelope the user can choose within)
    "cool_range_high_f": {
        "name": "Cool Range High",
        "device_class": None,
        "native_unit_of_measurement": "°F",
        "state_class": "measurement",
        "icon": "mdi:thermometer-high",
        "data_key": "cool_range_high_f",
    },
    "cool_range_low_f": {
        "name": "Cool Range Low",
        "device_class": None,
        "native_unit_of_measurement": "°F",
        "state_class": "measurement",
        "icon": "mdi:thermometer-low",
        "data_key": "cool_range_low_f",
    },
    "heat_range_high_f": {
        "name": "Heat Range High",
        "device_class": None,
        "native_unit_of_measurement": "°F",
        "state_class": "measurement",
        "icon": "mdi:thermometer-high",
        "data_key": "heat_range_high_f",
    },
    "heat_range_low_f": {
        "name": "Heat Range Low",
        "device_class": None,
        "native_unit_of_measurement": "°F",
        "state_class": "measurement",
        "icon": "mdi:thermometer-low",
        "data_key": "heat_range_low_f",
    },
    # Fan / ventilation config
    "fan_min_on_time_min": {
        "name": "Fan Min On Time",
        "device_class": "duration",
        "native_unit_of_measurement": "min",
        "state_class": "measurement",
        "icon": "mdi:fan",
        "data_key": "fan_min_on_time_min",
    },
    "ventilator_min_on_time_min": {
        "name": "Ventilator Min On Time",
        "device_class": "duration",
        "native_unit_of_measurement": "min",
        "state_class": "measurement",
        "icon": "mdi:air-conditioner",
        "data_key": "ventilator_min_on_time_min",
    },
    "ventilator_min_on_time_home_min": {
        "name": "Ventilator Min On Time Home",
        "device_class": "duration",
        "native_unit_of_measurement": "min",
        "state_class": "measurement",
        "icon": "mdi:air-conditioner",
        "data_key": "ventilator_min_on_time_home_min",
    },
    "ventilator_min_on_time_away_min": {
        "name": "Ventilator Min On Time Away",
        "device_class": "duration",
        "native_unit_of_measurement": "min",
        "state_class": "measurement",
        "icon": "mdi:air-conditioner",
        "data_key": "ventilator_min_on_time_away_min",
    },
    "smart_circulation": {
        "name": "Smart Circulation",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:refresh-circle",
        "data_key": "smart_circulation",
    },
    "ventilator_free_cooling": {
        "name": "Ventilator Free Cooling",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:snowflake-melt",
        "data_key": "ventilator_free_cooling",
    },
    # Dehumidification config (live settings, not runtime target)
    "dehumidifier_level_pct": {
        "name": "Dehumidifier Level",
        "device_class": "humidity",
        "native_unit_of_measurement": "%",
        "state_class": "measurement",
        "icon": "mdi:water-percent",
        "data_key": "dehumidifier_level_pct",
    },
    "dehumidify_overcool_offset_config": {
        "name": "Dehumidify Overcool Offset (Configured)",
        "device_class": None,
        "native_unit_of_measurement": "°F-delta",
        "state_class": "measurement",
        "icon": "mdi:thermometer-low",
        "data_key": "dehumidify_overcool_offset_config",
    },
    "dehumidifier_mode": {
        "name": "Dehumidifier Mode",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:tune",
        "data_key": "dehumidifier_mode",
    },
    "dehumidify_with_ac": {
        "name": "Dehumidify With AC",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:water-alert",
        "data_key": "dehumidify_with_ac",
    },
    "dehumidify_when_heating": {
        "name": "Dehumidify When Heating",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:water-alert-outline",
        "data_key": "dehumidify_when_heating",
    },
    # Equipment capability / system type flags
    "has_heat_pump": {
        "name": "Has Heat Pump",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:heat-pump",
        "data_key": "has_heat_pump",
    },
    "has_forced_air": {
        "name": "Has Forced Air",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:fan",
        "data_key": "has_forced_air",
    },
    "has_boiler": {
        "name": "Has Boiler",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:water-boiler",
        "data_key": "has_boiler",
    },
    "has_humidifier": {
        "name": "Has Humidifier",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:water",
        "data_key": "has_humidifier",
    },
    "has_dehumidifier": {
        "name": "Has Dehumidifier",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:water-off",
        "data_key": "has_dehumidifier",
    },
    "use_zone_controller": {
        "name": "Use Zone Controller",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:vector-arrange-above",
        "data_key": "use_zone_controller",
    },
    # Top-level mode flags
    "hvac_mode_setting": {
        "name": "HVAC Mode Setting",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:hvac",
        "data_key": "hvac_mode_setting",
    },
    "follow_me_comfort": {
        "name": "Follow Me Comfort",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:account-location",
        "data_key": "follow_me_comfort",
    },
    "auto_heat_cool_enabled": {
        "name": "Auto Heat Cool Enabled",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:autorenew",
        "data_key": "auto_heat_cool_enabled",
    },
    "cooling_lockout": {
        "name": "Cooling Lockout",
        "device_class": None,
        "native_unit_of_measurement": None,
        "state_class": None,
        "icon": "mdi:snowflake-off",
        "data_key": "cooling_lockout",
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
