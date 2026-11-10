import csv
from io import StringIO

import pytest

from app.user_access.services import AuthService
from s3_helpers import PASSWORD, demo, demo_data, login  # noqa: F401


@pytest.fixture()
def company_data(demo_data, monkeypatch):
    other_admin = AuthService.register(
        "Other Company",
        "admin@other.de",
        PASSWORD,
    )

    # Deliberately select the other company in the old development setting.
    # Logged-in users must still see their own company's data.
    monkeypatch.setenv(
        "ANALYTICS_DEV_COMPANY_ID",
        other_admin.company_id,
    )
    return other_admin


@pytest.mark.parametrize(
    "email",
    [
        "admin@demo.de",
        "manager@demo.de",
        "employee@demo.de",
    ],
)
def test_dashboard_uses_logged_in_company(client, company_data, email):
    assert login(client, email).status_code == 302

    response = client.get("/analytics/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo GmbH" in html
    assert "Other Company" not in html

    export = client.get("/analytics/?export=csv")
    assert export.status_code == 200
    assert export.mimetype == "text/csv"

    rows = list(csv.reader(StringIO(export.data.decode("utf-8-sig"))))
    assert rows[1] == ["Summary", "Total emissions", "1300.00", "6"]


def test_other_company_cannot_export_demo_records(client, company_data):
    assert login(client, "admin@other.de").status_code == 302

    response = client.get("/analytics/?export=csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"

    rows = list(csv.reader(StringIO(response.data.decode("utf-8-sig"))))
    assert rows[1] == ["Summary", "Total emissions", "0.00", "0"]