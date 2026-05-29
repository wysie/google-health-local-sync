from google_health_local_sync.storage import GoogleHealthStore


def test_store_roundtrips_token_and_raw_datapoint(tmp_path):
    store = GoogleHealthStore(tmp_path)
    store.save_token({"access_token": "a", "refresh_token": "r"})
    assert store.load_token()["refresh_token"] == "r"

    store.init_db()
    inserted = store.upsert_datapoint(
        data_type="sleep",
        data_point={"name": "users/me/dataTypes/sleep/dataPoints/1", "sleep": {"type": "CLASSIC"}},
    )
    inserted_again = store.upsert_datapoint(
        data_type="sleep",
        data_point={"name": "users/me/dataTypes/sleep/dataPoints/1", "sleep": {"type": "CLASSIC"}},
    )

    assert inserted is True
    assert inserted_again is False
    rows = store.list_datapoints("sleep")
    assert len(rows) == 1
    assert rows[0]["record_id"] == "users/me/dataTypes/sleep/dataPoints/1"
