"""
Qrater Auth.

Module with bluepring specific routes
"""

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import (LoginForm, RegistrationForm,
                            ResetPasswordRequestForm, ResetPasswordForm)
from app.models import Rater
from app.auth.email import send_password_reset_email


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        rater = Rater.query.filter_by(username=form.username.data).first()
        if rater is None or not rater.check_password(form.password.data):
            flash('Invalid username or password...', 'danger')
            return redirect(url_for('auth.login'))
        login_user(rater, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    """Log out."""
    logout_user()
    return redirect(url_for('main.dashboard'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Page to register new rater."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        rater = Rater(username=form.username.data, email=form.email.data)
        rater.set_password(form.password.data)
        db.session.add(rater)
        db.session.commit()
        flash('Congratulations, you are now a registered Rater!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)


# TODO: IMPLEMENT??
@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Page to request a password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        rater = Rater.query.filter_by(email=form.email.data).first()
        if rater:
            send_password_reset_email(rater)
        flash('Check your email for the instructions to reset your password',
              'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request',
                           title='Reset Password', form=form)


# TODO: IMPLEMENT??
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Page to reset the password."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    rater = Rater.verify_reset_password_token(token)
    if not rater:
        return redirect(url_for('main.dashboard'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        rater.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)
