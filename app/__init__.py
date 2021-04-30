"""
Qrater.

Flask webapplication for QC Neuroimaging data.
IN DEVELOPMENT
"""

import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from elasticsearch import Elasticsearch
from flask import Flask
from flask.logging import create_logger
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_messages = 'Please log in to access this page.'
login.login_message_category = 'info'
mail = Mail()
moment = Moment()


def create_app(config_class=Config):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.dt import bp as dt_bp
    app.register_blueprint(dt_bp, url_prefix='/dt')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug:
        # if app.config['MAIL_SERVER']:
            # auth = None
            # if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                # auth = (app.config['MAIL_USERNAME'],
                        # app.config['MAIL_PASSWORD'])
            # secure = None
            # if app.config['MAIL_USE_TLS']:
                # secure = ()
            # mail_handler = SMTPHandler(
                # mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                # fromaddr=f"no-reply@{app.config['MAIL_SERVER']}",
                # toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                # credentials=auth, secure=secure)
            # mail_handler.setLevel(logging.ERROR)
            # app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        logger = create_logger(app)
        file_handler = RotatingFileHandler('logs/qrater.log',
                                           maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        logger.setLevel(logging.INFO)
        logger.info('Qrater startup')

    return app


from app import models
