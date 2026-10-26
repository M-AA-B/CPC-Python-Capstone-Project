from flask import Blueprint
bp = Blueprint("access", __name__, url_prefix="/auth")
from . import routes
