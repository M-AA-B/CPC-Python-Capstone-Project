"""Subsystem 3 walkthrough — AI Assistant & User Access (Junaid Ahmad · 7222074).

Shows constructor, setup methods and getters/setters of every S3 class.
Runs offline; with OPENAI_API_KEY set (and `pip install openai`) the coach
answers through OpenAI instead.

    python demo_s3.py
"""
from app.ai_assistant import AIAssistant, AIClient, PromptBuilder
from app.user_access import AuthService


def main() -> None:
    # 1. User access: AuthService creates User objects with hashed passwords and roles
    auth = AuthService(default_company_id="ecotech-gmbh")
    manager = auth.register("manager@ecotech.de", "securePass123", role="manager", department_id="logistics")
    employee = auth.register("employee@ecotech.de", "securePass123")
    print(f"[User]           {manager.get_email()} role={manager.get_role()} | "
          f"{employee.get_email()} role={employee.get_role()}")
    print(f"[AuthService]    wrong password -> {auth.login('manager@ecotech.de', 'guess123456')}")
    auth.login("manager@ecotech.de", "securePass123")
    print(f"[AuthService]    logged in: {auth.get_active_user().get_email()} | "
          f"manager access: {auth.require_role('manager')}")
    try:
        auth.require_role("admin")
    except PermissionError as error:
        print(f"[AuthService]    {error}")

    # 2. PromptBuilder: only aggregated, anonymised figures go to the AI
    builder = PromptBuilder(max_hotspots=2)
    context = builder.build_context("ecotech-gmbh", {"company_vehicles": 670.0, "electricity": 420.0, "travel": 35.0})
    print(f"[PromptBuilder]  context sent to AI: {context}")

    # 3. AIClient: OpenAI settings with validation; the API key is never readable
    client = AIClient(model="gpt-4o-mini", timeout=10, max_tokens=600, daily_limit=200)
    client.configure(timeout=15)
    print(f"[AIClient]       model={client.get_model()} timeout={client.get_timeout()}s "
          f"key set={client.has_api_key()} available={client.is_available()}")

    # 4. AIAssistant composes PromptBuilder + AIClient
    coach = AIAssistant(prompt_builder=builder, client=client)
    reply = coach.ask(manager, "Where should we cut emissions first?", context)
    print(f"[ChatMessage]    {reply.get_sender()}: {reply.get_content()}")
    print(f"[AIAssistant]    history length: {len(coach.get_history())}")

    # 5. Recommendation workflow: proposed -> accepted -> done (a rejected tip cannot be done)
    tips = coach.recommend("logistics", context["top_hotspots"])
    first, second = tips
    first.set_est_cost_eur(2500)
    first.accept()
    first.mark_done()
    second.reject()
    for tip in tips:
        print(f"[Recommendation] {tip.get_title()} | saves {tip.get_est_saving_kg()} kg | "
              f"cost {tip.get_est_cost_eur()} EUR | {tip.get_status()}")
    try:
        second.mark_done()
    except ValueError as error:
        print(f"[Recommendation] {error}")

    print(f"[AIAssistant]    {coach.summarise('2026-03', {'company_vehicles': 670.0, 'electricity': 420.0})}")


if __name__ == "__main__":
    main()
