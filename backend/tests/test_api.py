import pytest

from cost_tracker.base import DIMENSIONS


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_summary_shape(client):
    s = client.get("/api/summary").json()
    assert s["last_month"] > 0
    assert s["projected_month"] >= s["month_to_date"] >= 0


@pytest.mark.parametrize("dim", [*DIMENSIONS, "TAG:team"])
def test_every_dimension_accounts_for_the_whole_bill(client, dim):
    params = {"start": "2026-09-01", "end": "2026-10-01"}
    r = client.get("/api/breakdown", params={**params, "group_by": dim}).json()
    assert r["total"] == pytest.approx(20.0 * 30)
    assert r["items"] == sorted(r["items"], key=lambda i: -i["amount"])
    assert sum(i["share"] for i in r["items"]) == pytest.approx(1)


def test_timeseries_monthly_buckets(client):
    r = client.get(
        "/api/timeseries",
        params={"start": "2026-06-01", "end": "2026-09-01", "granularity": "MONTHLY"},
    ).json()
    assert [p["start"] for p in r["periods"]] == ["2026-06-01", "2026-07-01", "2026-08-01"]
    for p in r["periods"]:
        assert sum(p["groups"].values()) == pytest.approx(p["total"])


@pytest.mark.parametrize(
    "params",
    [
        {"metric": "Bogus"},
        {"group_by": "NOPE"},
        {"start": "2026-05-02", "end": "2026-05-01"},
        {"start": "2020-01-01"},
    ],
)
def test_bad_params_rejected(client, params):
    assert client.get("/api/breakdown", params=params).status_code == 422


def test_ui_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()
