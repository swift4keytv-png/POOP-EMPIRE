import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "poop-empire-local-dev-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(ROOT, "instance", "empire.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    WTF_CSRF_TIME_LIMIT = None
    TEMPLATES_AUTO_RELOAD = True


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
