"""
Qrater DataTables.

Construction of blueprint
"""

from flask import Blueprint

bp = Blueprint('dt', __name__)

from app.dt import routes
