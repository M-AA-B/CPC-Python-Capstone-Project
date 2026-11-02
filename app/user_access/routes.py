"""S3 - login, registration, logout and user management pages (/auth/...)."""
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user

from app.models.user import Role
from app.user_access.permissions import check_csrf, require_role
from app.user_access.services import MIN_PASSWORD_LENGTH, AuthError, AuthService

from . import bp

AFTER_LOGIN = "analytics.index"


def _safe_next(target: str | None) -> str | None:
    """Only follow ?next= to pages on this site, never to another domain."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


@bp.get("/")
def index():
    """Account page when logged in, otherwise the login form."""
    if current_user.is_authenticated:
        return render_template("user_access/account.html")
    return render_template("user_access/login.html", email="")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(AFTER_LOGIN))

    email = ""
    if request.method == "POST":
        check_csrf()
        email = request.form.get("email", "")
        remember = request.form.get("remember") == "on"
        if AuthService.login(email, request.form.get("password", ""), remember):
            return redirect(_safe_next(request.args.get("next")) or url_for(AFTER_LOGIN))
        flash("Invalid email or password.", "danger")
    return render_template("user_access/login.html", email=email)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(AFTER_LOGIN))

    if request.method == "POST":
        check_csrf()
        form = request.form
        try:
            if form.get("password", "") != form.get("confirm", ""):
                raise AuthError("Passwords do not match.")
            user = AuthService.register(
                form.get("company_name", ""),
                form.get("email", ""),
                form.get("password", ""),
                form.get("departments", "").split(","),
                name=form.get("name"),
            )
        except AuthError as error:
            flash(str(error), "danger")
        else:
            login_user(user)
            flash("Company account created. You are the admin.", "success")
            return redirect(url_for(AFTER_LOGIN))
    return render_template("user_access/register.html", values=request.form,
                           min_length=MIN_PASSWORD_LENGTH)


@bp.post("/logout")
def logout():
    check_csrf()
    AuthService.logout()
    flash("You have been logged out.", "info")
    return redirect(url_for("access.login"))


@bp.route("/users", methods=["GET", "POST"])
@require_role(Role.ADMIN)
def users():
    """Admins see their company's users and add new ones."""
    if request.method == "POST":
        check_csrf()
        form = request.form
        try:
            AuthService.create_user(
                current_user,
                form.get("email", ""),
                form.get("password", ""),
                form.get("role", ""),
                form.get("department_id") or None,
                name=form.get("name"),
            )
        except AuthError as error:
            flash(str(error), "danger")
        else:
            flash(f"User {form.get('email', '').strip().lower()} added.", "success")
            return redirect(url_for("access.users"))

    departments = AuthService.company_departments(current_user.company_id)
    return render_template(
        "user_access/users.html",
        users=AuthService.company_users(current_user.company_id),
        departments=departments,
        department_names={d.id: d.name for d in departments},
        roles=Role.ALL,
        values=request.form,
        min_length=MIN_PASSWORD_LENGTH,
    )
