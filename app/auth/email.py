"""
Qrater Auth.

Email support
"""
from flask import render_template, current_app
from app.email import send_email


def send_password_reset_email(rater):
    """Send an email to reset password."""
    token = rater.get_reset_password_token()
    send_email('[Qrater] Reset Your Password',
               sender=current_app.config['ADMINS'][0],
               recipients=[rater.email],
               text_body=render_template('email/reset_password.txt',
                                         rater=rater, token=token),
               html_body=render_template('email/reset_password.html',
                                         rater=rater, token=token))
