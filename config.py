"""
Qrater Configuration.

Python script to load configuration values for Flask app.
They can be specified here or loaded from a dotfile (.env).
"""

import os
from dotenv import load_dotenv

basedir = os.path.realpath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Docker-compose: Secrets
# MySQL
# If environment variable use it
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    try:
        # Docker-compose secret
        secret = open('/run/secrets/db-password', encoding='utf-8')
    except FileNotFoundError:
        # If no db-password secret or ENV_VAR; use local SQLite
        DATABASE_URL = f"sqlite:///{os.path.join(basedir, 'SQL.db')}"
    else:
        db_password = secret.read().splitlines()[0]
        DATABASE_URL = f"mysql+pymysql://root:{db_password}@db/qrater"
    finally:
        secret.close()

# Mail
try:
    secret = open('/run/secrets/mail-password', encoding='utf-8')
except FileNotFoundError:
    mail_password = None
else:
    mail_password = secret.read().splitlines()[0] \
        if secret.read() != "" else None
finally:
    secret.close()


class Config():
    """Config class to be loaded by Flask app with config attributes."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = mail_password or os.environ.get('MAIL_PASSWORD')
    ADMINS = os.environ.get("ADMINS_MAIL").split(",") if \
        os.environ.get("ADMINS_MAIL") else None
    ABS_PATH = os.path.join(basedir, 'app')
    MAX_CONTENT_LENGTH = os.environ.get('MAX_CONTENT_LENGTH') or \
        1024 * 1024 * 1024  # 1GB
    DSET_ALLOWED_EXTS = os.environ.get("DSET_ALLOWED_EXTS") or \
        set(['png', 'jpg', 'jpeg'])
