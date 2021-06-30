"""
Qrater Data management.

Construction of blueprint
"""

from flask import Blueprint

bp = Blueprint('data', __name__)

from app.data import routes
