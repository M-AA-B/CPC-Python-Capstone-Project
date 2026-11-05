"""Hometask 3 — tests for the S3 JSON API and database access layer (Junaid Ahmad · 7222074).

Run with:  python -m unittest discover tests
Uses an in-memory SQLite database; the MySQL tests check the generated MySQL
table definitions and driver setup without needing a running MySQL server.
"""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app import create_app
from app.ai_assistant.repositories import ChatMessageRepository, RecommendationRepository
from app.ai_assistant.services import AIClient
from app.extensions import db
from app.models.chat_message import ChatMessage
from app.models.company import Company
from app.models.department import Department
from app.models.recommendation import Recommendation
from app.models.user import Role, User
from app.user_access.repositories import CompanyScopedRepository, UserRepository

PASSWORD = "securePass123"
S3_TABLES = ("users", "chat_messages", "recommendations", "ai_requests")


class S3ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "OPENAI_API_KEY": "",
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        self.company = Company(name="EcoTech GmbH")
        self.other_company = Company(name="Other AG")
        db.session.add_all([self.company, self.other_company])
        db.session.flush()
        self.logistics = Department(company_id=self.company.id, name="Logistics")
        self.office = Department(company_id=self.company.id, name="Office")
        self.other_dept = Department(company_id=self.other_company.id, name="Sales")
        db.session.add_all([self.logistics, self.office, self.other_dept])
        db.session.flush()

        self.admin = self._user("admin@ecotech.de", Role.ADMIN, self.company)
        self.manager = self._user("manager@ecotech.de", Role.MANAGER, self.company, self.logistics)
        self.employee = self._user("employee@ecotech.de", Role.EMPLOYEE, self.company, self.office)
        self.outsider = self._user("admin@other.de", Role.ADMIN, self.other_company)

        self.tip_logistics = self._tip(self.company, self.logistics, "Electric vans")
        self.tip_office = self._tip(self.company, self.office, "LED lighting")
        self.tip_other = self._tip(self.other_company, self.other_dept, "Not yours")
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _user(self, email, role, company, department=None):
        user = User(email=email, role=role, company_id=company.id,
                    department_id=department.id if department else None)
        user.set_password(PASSWORD)
        db.session.add(user)
        return user

    def _tip(self, company, department, title):
        tip = Recommendation(company_id=company.id, department_id=department.id, title=title,
                             description="Test tip", est_saving_kg=100.0, effort="low")
        db.session.add(tip)
        return tip

    def login(self, email):
        response = self.client.post("/api/s3/login", json={"email": email, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["csrf_token"]


class AuthApiTests(S3ApiTestCase):
    def test_requests_without_login_get_401_json(self):
        for path in ("/api/s3/me", "/api/s3/recommendations", "/api/s3/chat/history"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.get_json()["ok"])

    def test_login_checks_password_and_json(self):
        bad = self.client.post("/api/s3/login", json={"email": "admin@ecotech.de", "password": "wrongPass1"})
        self.assertEqual(bad.status_code, 401)
        not_json = self.client.post("/api/s3/login", data={"email": "admin@ecotech.de"})
        self.assertEqual(not_json.status_code, 400)

    def test_login_me_logout(self):
        token = self.login("Manager@EcoTech.de")
        me = self.client.get("/api/s3/me").get_json()
        self.assertEqual(me["user"]["role"], "manager")
        self.assertNotIn("password_hash", me["user"])
        self.assertEqual(self.client.post("/api/s3/logout").status_code, 400)  # no CSRF token
        self.assertEqual(self.client.post("/api/s3/logout", headers={"X-CSRFToken": token}).status_code, 200)
        self.assertEqual(self.client.get("/api/s3/me").status_code, 401)

    def test_users_list_is_admin_only_and_company_scoped(self):
        self.login("admin@ecotech.de")
        emails = [u["email"] for u in self.client.get("/api/s3/users").get_json()["users"]]
        self.assertEqual(emails, ["admin@ecotech.de", "employee@ecotech.de", "manager@ecotech.de"])
        managers = self.client.get("/api/s3/users?role=manager").get_json()["users"]
        self.assertEqual([u["email"] for u in managers], ["manager@ecotech.de"])
        self.assertEqual(self.client.get("/api/s3/users?role=boss").status_code, 400)

        self.login("employee@ecotech.de")
        forbidden = self.client.get("/api/s3/users")
        self.assertEqual(forbidden.status_code, 403)
        self.assertFalse(forbidden.get_json()["ok"])


class RecommendationApiTests(S3ApiTestCase):
    def titles(self, path="/api/s3/recommendations"):
        return sorted(r["title"] for r in self.client.get(path).get_json()["recommendations"])

    def test_admin_sees_company_employee_sees_own_department(self):
        self.login("admin@ecotech.de")
        self.assertEqual(self.titles(), ["Electric vans", "LED lighting"])
        self.login("employee@ecotech.de")
        self.assertEqual(self.titles(), ["LED lighting"])

    def test_other_company_and_other_department_are_hidden(self):
        self.login("admin@ecotech.de")
        self.assertEqual(self.client.get(f"/api/s3/recommendations/{self.tip_other.id}").status_code, 404)
        self.login("employee@ecotech.de")
        self.assertEqual(self.client.get(f"/api/s3/recommendations/{self.tip_logistics.id}").status_code, 404)
        own = self.client.get(f"/api/s3/recommendations/{self.tip_office.id}")
        self.assertEqual(own.get_json()["recommendation"]["title"], "LED lighting")

    def test_status_filter(self):
        self.tip_office.status = "accepted"
        db.session.commit()
        self.login("admin@ecotech.de")
        self.assertEqual(self.titles("/api/s3/recommendations?status=accepted"), ["LED lighting"])
        self.assertEqual(self.client.get("/api/s3/recommendations?status=maybe").status_code, 400)

    def test_patch_workflow_and_csrf(self):
        token = self.login("manager@ecotech.de")
        url = f"/api/s3/recommendations/{self.tip_logistics.id}"
        self.assertEqual(self.client.patch(url, json={"status": "accepted"}).status_code, 400)  # no token
        accepted = self.client.patch(url, json={"status": "accepted"}, headers={"X-CSRFToken": token})
        self.assertEqual(accepted.get_json()["recommendation"]["status"], "accepted")
        done = self.client.patch(url, json={"status": "done"}, headers={"X-CSRFToken": token})
        self.assertEqual(done.status_code, 200)
        reopen = self.client.patch(url, json={"status": "accepted"}, headers={"X-CSRFToken": token})
        self.assertEqual(reopen.status_code, 409)
        self.assertEqual(db.session.get(Recommendation, self.tip_logistics.id).status, "done")

    def test_patch_permissions(self):
        token = self.login("employee@ecotech.de")
        url = f"/api/s3/recommendations/{self.tip_office.id}"
        self.assertEqual(self.client.patch(url, json={"status": "accepted"},
                                           headers={"X-CSRFToken": token}).status_code, 403)
        token = self.login("admin@ecotech.de")
        other = f"/api/s3/recommendations/{self.tip_other.id}"
        self.assertEqual(self.client.patch(other, json={"status": "rejected"},
                                           headers={"X-CSRFToken": token}).status_code, 404)


class ChatApiTests(S3ApiTestCase):
    def test_history_is_own_and_ordered(self):
        start = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
        db.session.add_all([
            ChatMessage(user_id=self.manager.id, sender="user", content="First", created_at=start),
            ChatMessage(user_id=self.manager.id, sender="assistant", content="Second",
                        created_at=start + timedelta(seconds=2)),
            ChatMessage(user_id=self.employee.id, sender="user", content="Not mine", created_at=start),
        ])
        db.session.commit()
        self.login("manager@ecotech.de")
        messages = self.client.get("/api/s3/chat/history").get_json()["messages"]
        self.assertEqual([m["content"] for m in messages], ["First", "Second"])
        self.assertEqual(len(self.client.get("/api/s3/chat/history?limit=1").get_json()["messages"]), 1)
        self.assertEqual(self.client.get("/api/s3/chat/history?limit=abc").status_code, 400)

    def test_chat_validates_and_reports_missing_ai(self):
        token = self.login("manager@ecotech.de")
        empty = self.client.post("/api/s3/chat", json={"question": "  "}, headers={"X-CSRFToken": token})
        self.assertEqual(empty.status_code, 400)
        no_key = self.client.post("/api/s3/chat", json={"question": "Biggest source?"},
                                  headers={"X-CSRFToken": token})
        self.assertEqual(no_key.status_code, 503)
        self.assertIn("OPENAI_API_KEY", no_key.get_json()["error"])

    def test_ai_usage_for_admin(self):
        self.login("admin@ecotech.de")
        usage = self.client.get("/api/s3/ai-usage").get_json()
        self.assertEqual((usage["requests_today"], usage["tokens_today"]), (0, 0))
        self.assertEqual(usage["daily_limit"], 200)


class RepositoryTests(S3ApiTestCase):
    def test_repository_needs_a_company(self):
        with self.assertRaises(ValueError):
            UserRepository("")

    def test_get_never_crosses_companies(self):
        repo = RecommendationRepository(self.company.id)
        self.assertIsNone(repo.get(self.tip_other.id))
        self.assertEqual(repo.count(), 2)
        self.assertEqual(UserRepository(self.other_company.id).count(), 1)

    def test_save_refuses_other_company(self):
        with self.assertRaises(PermissionError):
            RecommendationRepository(self.company.id).save(self.tip_other)
        foreign = ChatMessage(user_id=self.outsider.id, sender="user", content="Hi")
        with self.assertRaises(PermissionError):
            ChatMessageRepository(self.company.id).save(foreign)

    def test_base_class_is_reused_by_subclasses(self):
        for repo_class in (UserRepository, RecommendationRepository, ChatMessageRepository):
            self.assertTrue(issubclass(repo_class, CompanyScopedRepository))


class MySQLCompatibilityTests(S3ApiTestCase):
    def test_s3_tables_compile_for_mysql(self):
        dialect = mysql.dialect()
        for name in S3_TABLES:
            ddl = str(CreateTable(db.metadata.tables[name]).compile(dialect=dialect))
            self.assertIn(f"CREATE TABLE {name}", ddl)
            self.assertNotIn("VARCHAR,", ddl)  # MySQL needs a length on every VARCHAR
        users = str(CreateTable(db.metadata.tables["users"]).compile(dialect=dialect))
        self.assertIn("UNIQUE (email)", users)

    def test_mysql_driver_and_url(self):
        engine = create_engine("mysql+pymysql://carbon_user:secret@localhost:3306/carbon_tracker?charset=utf8mb4")
        self.assertEqual((engine.dialect.name, engine.dialect.driver), ("mysql", "pymysql"))
        import cryptography  # noqa: F401  needed by PyMySQL for MySQL 8 logins


class AIClientTimeoutTests(unittest.TestCase):
    def test_changed_timeout_reaches_openai_client(self):
        client = AIClient("sk-test", "gpt-4o-mini", timeout=10)
        client.timeout = 30
        self.assertEqual(client._client.timeout, 30.0)


if __name__ == "__main__":
    unittest.main()
