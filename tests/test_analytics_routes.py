import csv
from io import StringIO

import pytest

from app.extensions import db
from app.models.company import Company
from app.models.target import Target


@pytest.fixture()
def analytics_client(client, monkeypatch):
    monkeypatch.setenv("ANALYTICS_DEV_COMPANY_ID", "route-company")
    client.application.config["DEBUG"] = True

    with client.application.app_context():
        db.session.add(
            Company(id="route-company", name="Route Test Company")
        )
        db.session.commit()

    return client


def target_form_data():
    return {
        "baseline_start": "2020-01-01",
        "baseline_end": "2020-01-31",
        "period_start": "2020-03-01",
        "period_end": "2020-03-31",
        "reduction_percent": "20",
    }


def get_form_token(client):
    response = client.get("/analytics/target")
    assert response.status_code == 200

    with client.session_transaction() as session:
        return session["target_form_token"]


def test_dashboard_renders_empty_company(analytics_client):
    response = analytics_client.get("/analytics/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Emissions Dashboard" in html
    assert "Route Test Company" in html
    assert "No reduction target has been set." in html


def test_target_form_renders(analytics_client):
    response = analytics_client.get("/analytics/target")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Save target" in html
    assert 'name="csrf_token"' in html


def test_csv_download_for_empty_results(analytics_client):
    response = analytics_client.get("/analytics/?export=csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment;" in response.headers["Content-Disposition"]

    content = response.data.decode("utf-8-sig")
    rows = list(csv.reader(StringIO(content)))

    assert rows[0] == [
        "Section",
        "Label",
        "Emissions (kg CO2e)",
        "Record count",
    ]
    assert rows[1] == ["Summary", "Total emissions", "0.00", "0"]


def test_invalid_dates_do_not_download_csv(analytics_client):
    response = analytics_client.get(
        "/analytics/?start_date=2026-04-30"
        "&end_date=2026-04-01&export=csv"
    )

    assert response.mimetype == "text/html"
    assert "Content-Disposition" not in response.headers
    assert (
        "Start date must be on or before end date."
        in response.get_data(as_text=True)
    )


def test_target_save_assigns_server_selected_company(analytics_client):
    data = target_form_data()
    data["csrf_token"] = get_form_token(analytics_client)
    data["company_id"] = "another-company"

    response = analytics_client.post("/analytics/target", data=data)

    assert response.status_code == 302

    with analytics_client.application.app_context():
        targets = db.session.execute(db.select(Target)).scalars().all()

        assert len(targets) == 1
        assert targets[0].company_id == "route-company"
        assert targets[0].reduction_percent == 20
        assert targets[0].data_complete is False

    dashboard = analytics_client.get("/analytics/")
    assert dashboard.status_code == 200
    assert "Reduce company emissions by" in dashboard.get_data(as_text=True)


def test_invalid_target_is_not_saved(analytics_client):
    data = target_form_data()
    data["csrf_token"] = get_form_token(analytics_client)
    data["reduction_percent"] = "101"

    response = analytics_client.post("/analytics/target", data=data)

    assert "Reduction must be" in response.get_data(as_text=True)

    with analytics_client.application.app_context():
        assert db.session.execute(db.select(Target)).scalars().all() == []


def test_target_rejects_missing_csrf_token(analytics_client):
    response = analytics_client.post(
        "/analytics/target",
        data=target_form_data(),
    )

    assert response.status_code == 400

    with analytics_client.application.app_context():
        assert db.session.execute(db.select(Target)).scalars().all() == []


def test_target_editing_disabled_outside_debug_mode(analytics_client):
    analytics_client.application.config["DEBUG"] = False

    assert analytics_client.get("/analytics/target").status_code == 403
    assert analytics_client.post("/analytics/target").status_code == 403