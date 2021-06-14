"""
Qrater Configuration.

Python script to load configuration values for Flask app.
They can be specified here or loaded from a dotfile (.env).
"""

import os
from dotenv import load_dotenv

basedir = os.path.realpath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

## Docker-compose: Secrets
# MySQL
try:
    secret = open('db-password.txt', encoding='utf-8')
except FileNotFoundError:
    # If no db-password secret check for DATABASE_URL environment variable
    DATABASE_URL = os.environ.get('DATABASE_URL')
else:
    db-password = secret.read().splitlines()[0]
    DATABASE_URL = f"mysql+pymysql://root:{db-password}@db/qrater"
    secret.close()

# Mail
try:
    secret = open('mail-password.txt', encoding='utf-8')
except FileNotFoundError:
    mail-password = None
else:
    mail-password = secret.read().splitlines()[0]
    secret.close()

class Config():
    """Config class to be loaded by Flask app with config attributes."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL #or \
        #'sqlite:///' + os.path.join(basedir, "SQL.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = mail-password or os.environ.get('MAIL_PASSWORD')
    ADMINS = [admin for admin in os.environ.get("ADMINS_MAIL").split(",")]
    ABS_PATH = os.path.join(basedir, 'app')
    MAX_CONTENT_LENGTH = os.environ.get('MAX_CONTENT_LENGTH') or \
        1024 * 1024 * 1024  # 1GB
    DSET_ALLOWED_EXTS = os.environ.get("DSET_ALLOWED_EXTS") or \
        set(['png', 'jpg', 'jpeg'])
