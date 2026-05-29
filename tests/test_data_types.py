from google_health_local_sync.data_types import DEFAULT_SYNC_DATA_TYPES, GOOGLE_HEALTH_DATA_TYPES, REFERENCE_DATA_TYPES


def test_reference_data_is_not_synced_by_default():
    assert "food" in GOOGLE_HEALTH_DATA_TYPES
    assert "food-measurement-unit" in GOOGLE_HEALTH_DATA_TYPES
    assert REFERENCE_DATA_TYPES == {"food", "food-measurement-unit"}
    assert "food" not in DEFAULT_SYNC_DATA_TYPES
    assert "food-measurement-unit" not in DEFAULT_SYNC_DATA_TYPES
    assert "nutrition-log" in DEFAULT_SYNC_DATA_TYPES
    assert "hydration-log" in DEFAULT_SYNC_DATA_TYPES
