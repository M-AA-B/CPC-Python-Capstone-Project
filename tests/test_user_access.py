"""S3 - registration, login, passwords, roles and CSRF. Owner: Junaid."""
import pytest

from app.extensions import db
from app.models.company import Company
from app.models.department import Department
from app.models.user import Role, User
from app.user_access.permissions import require_role
from app.user_access.services import AuthError, AuthService

PASSWORD = "demo1234"
TOKEN = "test-csrf-token"


@pytest.fixture()
def app(client):
    return client.application


@pytest.fixture()
def protected_page(app):
    """A page only admins and managers may open (S1/S2 pages will use require_role like this)."""

    @require_role(Role.ADMIN, Role.MANAGER)
    def manager_page():
        return "manager page"

    app.add_url_rule("/test/manager-page", "manager_page", manager_page)
    return "/test/manager-page"


@pytest.fixture()
def demo(client):
    """Demo GmbH with an admin, a manager and an employee (password demo1234)."""
    admin = AuthService.register("Demo GmbH", "admin@demo.de", PASSWORD, ["Logistics", "Office"])
    office = get_department("Office")
    AuthService.create_user(admin, "manager@demo.de", PASSWORD, Role.MANAGER, office.id)
    AuthService.create_user(admin, "employee@demo.de", PASSWORD, Role.EMPLOYEE, office.id)
    return admin


def get_user(email):
    return db.session.scalar(db.select(User).filter_by(email=email))


def get_department(name):
    return db.session.scalar(db.select(Department).filter_by(name=name))


def post(client, url, data, token=TOKEN):
    """POST a form like the browser does: the session holds the CSRF token, the form sends it."""
    with client.session_transaction() as session:
        session["csrf_token"] = TOKEN
    return client.post(url, data={**data, "csrf_token": token})


def login(client, email, password=PASSWORD):
    return post(client, "/auth/login", {"email": email, "password": password})


# --- passwords -------------------------------------------------------------

def test_password_is_stored_as_salted_hash(demo):
    admin, manager = get_user("admin@demo.de"), get_user("manager@demo.de")
    assert PASSWORD not in admin.password_hash
    assert admin.password_hash != manager.password_hash  # same password, different salt
    assert admin.check_password(PASSWORD)
    assert not admin.check_password("wrong-password")


def test_user_without_password_cannot_log_in(client):
    # S1's seed/test users only have id, email and name
    db.session.add(User(id="user-123", email="test@example.com", name="Test User"))
    db.session.commit()
    assert get_user("test@example.com").role == Role.EMPLOYEE
    assert AuthService.authenticate("test@example.com", "") is None


# --- registration ----------------------------------------------------------

def test_register_creates_company_admin_and_departments(client):
    user = AuthService.register("Green AG", " Boss@Green.de ", "secret123",
                                ["Office", " IT ", "Office", ""], name="Ada")
    assert user.role == Role.ADMIN
    assert user.email == "boss@green.de"
    assert user.name == "Ada"
    company = db.session.get(Company, user.company_id)
    assert company.name == "Green AG"
    assert sorted(d.name for d in company.departments) == ["IT", "Office"]


@pytest.mark.parametrize("company, email, password, message", [
    ("", "a@b.de", "secret123", "company name"),
    ("X", "not-an-email", "secret123", "valid email"),
    ("X", "a@b.de", "short", "at least 8"),
    ("X", "admin@demo.de", "secret123", "already exists"),
    ("Demo GmbH", "new@demo.de", "secret123", "already registered"),
])
def test_register_rejects_invalid_input(demo, company, email, password, message):
    with pytest.raises(AuthError, match=message):
        AuthService.register(company, email, password)


def test_register_page_logs_new_admin_in(client):
    response = post(client, "/auth/register", {
        "company_name": "Green AG", "departments": "Office", "email": "boss@green.de",
        "password": "secret123", "confirm": "secret123",
    })
    assert response.status_code == 302
    assert client.get("/auth/users").status_code == 200  # logged in as admin


def test_register_page_rejects_mismatched_passwords(client):
    response = post(client, "/auth/register", {
        "company_name": "Green AG", "email": "boss@green.de",
        "password": "secret123", "confirm": "different1",
    })
    assert b"Passwords do not match" in response.data
    assert get_user("boss@green.de") is None


# --- login / logout --------------------------------------------------------

def test_login_page_is_shown_to_guests(client):
    response = client.get("/auth/")
    assert response.status_code == 200
    assert b"Log in" in response.data


def test_login_with_correct_password(demo, client):
    response = login(client, "manager@demo.de")
    assert response.status_code == 302
    assert response.headers["Location"] == "/analytics/"
    assert b"manager@demo.de" in client.get("/auth/").data  # account page


def test_login_is_case_insensitive_for_email(demo, client):
    assert login(client, "Manager@Demo.DE").status_code == 302


@pytest.mark.parametrize("email, password", [
    ("manager@demo.de", "wrong-password"),
    ("nobody@demo.de", PASSWORD),
])
def test_login_fails_with_same_message(demo, client, email, password):
    response = login(client, email, password)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_login_follows_safe_next_only(demo, client):
    data = {"email": "manager@demo.de", "password": PASSWORD}
    assert post(client, "/auth/login?next=/activities/", data).headers["Location"] == "/activities/"
    post(client, "/auth/logout", {})
    response = post(client, "/auth/login?next=https://evil.example", data)
    assert response.headers["Location"] == "/analytics/"


def test_logout(demo, client, protected_page):
    login(client, "manager@demo.de")
    assert client.get(protected_page).status_code == 200
    post(client, "/auth/logout", {})
    response = client.get(protected_page)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# --- CSRF ------------------------------------------------------------------

@pytest.mark.parametrize("token", ["", "wrong-token"])
def test_post_without_valid_csrf_token_is_rejected(demo, client, token):
    response = post(client, "/auth/login",
                    {"email": "manager@demo.de", "password": PASSWORD}, token=token)
    assert response.status_code == 400


def test_pages_include_csrf_token(client):
    assert b'name="csrf_token"' in client.get("/auth/login").data


# --- role-based access -----------------------------------------------------

@pytest.mark.parametrize("email, manager_page, users_page", [
    ("admin@demo.de", 200, 200),
    ("manager@demo.de", 200, 403),
    ("employee@demo.de", 403, 403),
])
def test_pages_by_role(demo, client, protected_page, email, manager_page, users_page):
    login(client, email)
    assert client.get(protected_page).status_code == manager_page
    assert client.get("/auth/users").status_code == users_page


def test_guest_is_sent_to_login(client, protected_page):
    response = client.get(protected_page)
    assert response.status_code == 302
    assert "/auth/login?next=" in response.headers["Location"]


# --- admin adds users ------------------------------------------------------

def test_admin_adds_employee_via_page(demo, client):
    login(client, "admin@demo.de")
    response = post(client, "/auth/users", {
        "email": "new@demo.de", "password": "secret123",
        "role": Role.EMPLOYEE, "department_id": get_department("Office").id,
    })
    assert response.status_code == 302
    new_user = get_user("new@demo.de")
    assert new_user.role == Role.EMPLOYEE
    assert new_user.company_id == demo.company_id


def test_users_page_lists_only_own_company(demo, client):
    AuthService.register("Other AG", "boss@other.de", "secret123")
    login(client, "admin@demo.de")
    page = client.get("/auth/users").data
    assert b"employee@demo.de" in page
    assert b"boss@other.de" not in page


def test_only_admin_can_create_users(demo):
    with pytest.raises(AuthError, match="Only admins"):
        AuthService.create_user(get_user("manager@demo.de"), "x@demo.de", "secret123",
                                Role.EMPLOYEE, get_department("Office").id)


@pytest.mark.parametrize("role, department, message", [
    (Role.EMPLOYEE, None, "need a department"),
    ("boss", "Office", "Unknown role"),
])
def test_create_user_rejects_invalid_role_or_department(demo, role, department, message):
    department_id = get_department(department).id if department else None
    with pytest.raises(AuthError, match=message):
        AuthService.create_user(demo, "x@demo.de", "secret123", role, department_id)


def test_cannot_add_user_to_other_companys_department(demo):
    other_admin = AuthService.register("Other AG", "boss@other.de", "secret123", ["Sales"])
    with pytest.raises(AuthError, match="Unknown department"):
        AuthService.create_user(other_admin, "x@other.de", "secret123", Role.EMPLOYEE,
                                get_department("Office").id)  # Office belongs to Demo GmbH
