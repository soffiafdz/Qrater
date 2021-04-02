"""
Qrater Errors.

HTTP Error Handling
"""

from flask import render_template
from app import db
from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):
    """Redirect to 404 html template."""
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    """Redirect to 500 html template."""
    db.session.rollback()
    return render_template('errors/500.html'), 500


@bp.app_errorhandler(413)
def entity_too_large_error(error):
    """Redirect to 413 html template."""
    return render_template('errors/413.html'), 413
