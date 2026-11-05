"""Hometask 1 — unit tests for the Subsystem 3 classes (Junaid Ahmad · 7222074).

Run with:  python -m unittest discover tests
OpenAI is replaced by a fake module, so no API key or network is needed.
"""
import sys
import types
import unittest
from unittest import mock

from app.ai_assistant import AIAssistant, AIClient, PromptBuilder
from app.models import ChatMessage, Recommendation, User
from app.user_access import AuthService


def fake_openai(answer="Switch two vans to electric.", fail=False):
    """A stand-in for the `openai` package that records what it was asked."""
    module = types.ModuleType("openai")
    module.OpenAIError = type("OpenAIError", (Exception,), {})
    module.calls = []

    class Completions:
        def create(self, **kwargs):
            module.calls.append(kwargs)
            if fail:
                raise module.OpenAIError("service down")
            message = types.SimpleNamespace(content=answer)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class OpenAI:
        def __init__(self, api_key, timeout, max_retries):
            module.timeout = timeout
            self.chat = types.SimpleNamespace(completions=Completions())

    module.OpenAI = OpenAI
    return module


class UserTests(unittest.TestCase):
    def test_constructor_normalises_email_and_hashes_password(self):
        user = User("c1", "  Manager@EcoTech.de ", "securePass123", role="Manager")
        self.assertEqual(user.get_email(), "manager@ecotech.de")
        self.assertEqual(user.get_role(), "manager")
        self.assertNotIn("securePass123", user._password_hash)
        self.assertTrue(user.check_password("securePass123"))
        self.assertFalse(user.check_password("wrongPass123"))

    def test_same_password_gives_different_hashes(self):
        a = User("c1", "a@x.de", "securePass123")
        b = User("c1", "b@x.de", "securePass123")
        self.assertNotEqual(a._password_hash, b._password_hash)

    def test_setters_validate(self):
        user = User("c1", "a@x.de", "securePass123")
        with self.assertRaises(ValueError):
            user.set_role("superuser")
        with self.assertRaises(ValueError):
            user.set_email("no-at-sign")
        with self.assertRaises(ValueError):
            user.set_password("short")


class ChatMessageTests(unittest.TestCase):
    def test_to_dict_and_validation(self):
        msg = ChatMessage("u1", "User", "  How can we cut emissions?  ")
        self.assertEqual(msg.to_dict()["sender"], "user")
        self.assertEqual(msg.get_content(), "How can we cut emissions?")
        with self.assertRaises(ValueError):
            msg.set_content("   ")
        with self.assertRaises(ValueError):
            msg.set_sender("system")


class RecommendationTests(unittest.TestCase):
    def make(self):
        return Recommendation("d1", "Switch to LED lighting", 120.04, effort="low", est_cost_eur=800)

    def test_constructor_and_getters(self):
        tip = self.make()
        self.assertEqual(tip.get_status(), "proposed")
        self.assertEqual(tip.get_est_saving_kg(), 120.0)
        self.assertEqual(tip.get_est_cost_eur(), 800.0)

    def test_workflow_proposed_accepted_done(self):
        tip = self.make()
        tip.accept()
        tip.mark_done()
        self.assertEqual(tip.get_status(), "done")

    def test_rejected_tip_cannot_be_done(self):
        tip = self.make()
        tip.reject()
        with self.assertRaises(ValueError):
            tip.mark_done()

    def test_negative_values_rejected(self):
        with self.assertRaises(ValueError):
            Recommendation("d1", "Bad tip", -5)
        with self.assertRaises(ValueError):
            self.make().set_est_cost_eur(-1)


class AuthServiceTests(unittest.TestCase):
    def test_register_login_and_roles(self):
        auth = AuthService(default_company_id="c1")
        user = auth.register("emp@x.de", "securePass123")
        self.assertEqual(user.get_role(), "employee")
        self.assertIsNone(auth.login("emp@x.de", "wrongPass123"))
        self.assertIs(auth.login("EMP@x.de", "securePass123"), user)
        self.assertTrue(auth.require_role("employee"))
        with self.assertRaises(PermissionError):
            auth.require_role("admin")

    def test_duplicate_email_rejected(self):
        auth = AuthService()
        auth.register("a@x.de", "securePass123")
        with self.assertRaises(ValueError):
            auth.register("A@X.de", "otherPass123")


class PromptBuilderTests(unittest.TestCase):
    def test_context_is_aggregated_and_anonymised(self):
        builder = PromptBuilder(max_hotspots=2)
        context = builder.build_context("company-42", {"fuel": 670.0, "electricity": 420.0, "travel": 10.0})
        self.assertEqual(context["total_co2e_kg"], 1100.0)
        self.assertEqual(list(context["top_hotspots"]), ["fuel", "electricity"])
        self.assertNotIn("company-42", str(context))
        # stable across calls (and across runs, unlike hash())
        self.assertEqual(context["company_ref"], PromptBuilder.anonymise("company-42"))

    def test_chat_messages_include_history(self):
        builder = PromptBuilder()
        earlier = [ChatMessage("u1", "user", "Hi"), ChatMessage("u1", "assistant", "Hello")]
        messages = builder.chat_messages({"total_co2e_kg": 5}, "What next?", earlier)
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[-1]["content"], "What next?")

    def test_setters_validate(self):
        builder = PromptBuilder()
        with self.assertRaises(ValueError):
            builder.set_system_prompt("  ")
        with self.assertRaises(ValueError):
            builder.set_max_hotspots(0)


class AIClientTests(unittest.TestCase):
    def test_configure_and_validation(self):
        client = AIClient(api_key="")
        client.configure(model="gpt-4.1-mini", timeout=15, max_tokens=400, daily_limit=5)
        self.assertEqual(client.get_model(), "gpt-4.1-mini")
        self.assertEqual(client.get_timeout(), 15.0)
        self.assertFalse(client.is_available())
        for bad in (lambda: client.set_timeout(0), lambda: client.set_max_tokens(0),
                    lambda: client.set_daily_limit(-1), lambda: client.set_model(" ")):
            with self.assertRaises(ValueError):
                bad()

    def test_complete_uses_current_settings(self):
        fake = fake_openai()
        client = AIClient(api_key="sk-test", timeout=10)
        client.set_timeout(30)  # changed after construction: must still apply
        with mock.patch.dict(sys.modules, {"openai": fake}):
            answer = client.complete([{"role": "user", "content": "Hi"}])
        self.assertEqual(answer, "Switch two vans to electric.")
        self.assertEqual(fake.timeout, 30.0)
        self.assertEqual(fake.calls[0]["model"], "gpt-4o-mini")
        self.assertEqual(client.get_requests_today(), 1)

    def test_daily_limit_and_missing_key(self):
        with self.assertRaises(RuntimeError):
            AIClient(api_key="").complete([])
        client = AIClient(api_key="sk-test", daily_limit=0)
        self.assertFalse(client.is_available())
        with self.assertRaises(RuntimeError):
            client.complete([])

    def test_api_error_becomes_safe_message(self):
        with mock.patch.dict(sys.modules, {"openai": fake_openai(fail=True)}):
            with self.assertRaises(RuntimeError) as caught:
                AIClient(api_key="sk-test").complete([])
        self.assertIn("not available", str(caught.exception))


class AIAssistantTests(unittest.TestCase):
    def setUp(self):
        self.user = User("c1", "m@x.de", "securePass123", role="manager")
        self.context = PromptBuilder().build_context("c1", {"fuel": 670.0, "electricity": 420.0})

    def test_offline_answer_without_key(self):
        coach = AIAssistant(client=AIClient(api_key=""))
        reply = coach.ask(self.user, "Where do we start?", self.context)
        self.assertIn("1090.0 kg CO2e", reply.get_content())
        self.assertEqual(len(coach.get_history()), 2)

    def test_answer_from_openai_with_key(self):
        fake = fake_openai("Start with the fuel used by your vans.")
        coach = AIAssistant(client=AIClient(api_key="sk-test"))
        with mock.patch.dict(sys.modules, {"openai": fake}):
            coach.ask(self.user, "First question", self.context)
            reply = coach.ask(self.user, "Follow-up", self.context)
        self.assertEqual(reply.get_content(), "Start with the fuel used by your vans.")
        sent = fake.calls[1]["messages"]
        self.assertIn("1090.0", sent[0]["content"])         # aggregated figures only
        self.assertEqual(len(sent), 4)                        # system + 2 earlier + new question
        self.assertEqual(sent[-1]["content"], "Follow-up")   # history kept for follow-ups

    def test_api_failure_falls_back_to_offline_answer(self):
        coach = AIAssistant(client=AIClient(api_key="sk-test"))
        with mock.patch.dict(sys.modules, {"openai": fake_openai(fail=True)}):
            reply = coach.ask(self.user, "Where do we start?", self.context)
        self.assertIn("primary hotspot: fuel", reply.get_content())

    def test_model_setter_delegates_to_client_and_types_checked(self):
        client = AIClient(api_key="")
        coach = AIAssistant(model="gpt-4.1-mini", client=client)
        self.assertEqual(client.get_model(), "gpt-4.1-mini")
        with self.assertRaises(TypeError):
            coach.set_client("not a client")
        with self.assertRaises(TypeError):
            coach.set_prompt_builder("not a builder")

    def test_recommend_and_summarise(self):
        coach = AIAssistant(client=AIClient(api_key=""))
        tips = coach.recommend("d1", self.context["top_hotspots"])
        self.assertEqual([t.get_est_saving_kg() for t in tips], [100.5, 63.0])
        self.assertIn("1090.0 kg CO2e", coach.summarise("2026-03", {"fuel": 670.0, "electricity": 420.0}))


if __name__ == "__main__":
    unittest.main()
