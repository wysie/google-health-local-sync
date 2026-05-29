from __future__ import annotations

# Google Health API v4 data type collections listed in
# https://developers.google.com/health/data-types.
# Keep this as the raw archive target list; report-specific parsers can be
# layered on top without narrowing what gets synced.
GOOGLE_HEALTH_DATA_TYPES = [
    "active-energy-burned",
    "active-minutes",
    "active-zone-minutes",
    "activity-level",
    "altitude",
    "blood-glucose",
    "body-fat",
    "calories-in-heart-rate-zone",
    "core-body-temperature",
    "daily-heart-rate-variability",
    "daily-heart-rate-zones",
    "daily-oxygen-saturation",
    "daily-respiratory-rate",
    "daily-resting-heart-rate",
    "daily-sleep-temperature-derivations",
    "daily-vo2-max",
    "distance",
    "electrocardiogram",
    "exercise",
    "floors",
    "food",
    "food-measurement-unit",
    "heart-rate",
    "heart-rate-variability",
    "height",
    "hydration-log",
    "irregular-rhythm-notification",
    "nutrition-log",
    "oxygen-saturation",
    "respiratory-rate-sleep-summary",
    "run-vo2-max",
    "sedentary-period",
    "sleep",
    "steps",
    "swim-lengths-data",
    "time-in-heart-rate-zone",
    "total-calories",
    "vo2-max",
    "weight",
]

REFERENCE_DATA_TYPES = {
    # These are public nutrition catalogue/lookup tables, not YC's personal
    # logged meals. Keep them out of default personal-health sync unless the
    # caller explicitly asks for reference data.
    "food",
    "food-measurement-unit",
}

DEFAULT_SYNC_DATA_TYPES = [dt for dt in GOOGLE_HEALTH_DATA_TYPES if dt not in REFERENCE_DATA_TYPES]

# These collections either do not support list, or daily rollups are the safer
# product-level summary to archive alongside raw samples. Google limits some of
# them to 14-day dailyRollUp ranges, so CLI chunks them automatically.
# NOTE: `vo2-max` looks rollup-like, but live API reports dailyRollUp unsupported.
DAILY_ROLLUP_DATA_TYPES = {
    "calories-in-heart-rate-zone",
    "floors",
    "heart-rate",
    "total-calories",
}

ROLLUP_14_DAY_MAX_TYPES = {
    "calories-in-heart-rate-zone",
    "heart-rate",
    "active-minutes",
    "total-calories",
}

# Data types whose list endpoint accepts an interval.start_time filter. Some
# collection IDs use snake_case inside the filter expression even though the URL
# collection uses kebab-case. Do not add session/sample types here unless verified
# against the live API: exercise, run-vo2-max, and vo2-max reject these filters.
INTERVAL_FILTER_MEMBERS = {
    "active-energy-burned": "active_energy_burned.interval.start_time",
    "active-minutes": "active_minutes.interval.start_time",
    "active-zone-minutes": "active_zone_minutes.interval.start_time",
    "activity-level": "activity_level.interval.start_time",
    "altitude": "altitude.interval.start_time",
    "calories-in-heart-rate-zone": "calories_in_heart_rate_zone.interval.start_time",
    "distance": "distance.interval.start_time",
    "floors": "floors.interval.start_time",
    "sedentary-period": "sedentary_period.interval.start_time",
    "steps": "steps.interval.start_time",
    "swim-lengths-data": "swim_lengths_data.interval.start_time",
    "time-in-heart-rate-zone": "time_in_heart_rate_zone.interval.start_time",
}
