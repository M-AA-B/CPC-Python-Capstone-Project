from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# S3 (User Access): keeps track of the logged-in user (current_user).
login_manager = LoginManager()
login_manager.login_view = "access.login"
login_manager.login_message = "Please log in to open this page."
login_manager.login_message_category = "info"
