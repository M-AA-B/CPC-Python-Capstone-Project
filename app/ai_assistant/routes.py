from flask import render_template
from . import bp

@bp.get("/")
def index():
    return render_template("ai_assistant/index.html")
