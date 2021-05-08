"""
Qrater Configuration.

Python script to load configuration values for Flask app.
They can be specified here or loaded from a dotfile (.env).
"""

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config():
    """Config class to be loaded by Flask app with config attributes."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, "SQL.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMINS = ['soffiafdz@gmail.com']
    MAX_CONTENT_LENGTH = os.environ.get('MAX_CONTENT_LENGTH') or \
        1024 * 1024 * 1024  # 1GB
    DSET_ALLOWED_EXTS = os.environ.get("DSET_ALLOWED_EXTS") or \
        set(['png', 'jpg', 'jpeg'])
