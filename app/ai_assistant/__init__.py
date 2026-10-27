from flask import Blueprint

bp = Blueprint("assistant", __name__, url_prefix="/assistant")
from . import routes
