"""
Qrater.

Global app module with Flask models.
"""

# MODIFY...
from datetime import datetime
from hashlib import md5
from time import time
import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login


class Rater(UserMixin, db.Model):
    """SQLALCHEMY Model of Raters (Users)."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    ratings = db.relationship("Ratings", backref="rater", lazy="dynamic")
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """Object representation."""
        return f'<Rater {self.username}>'

    def set_password(self, password):
        """Generate password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password validity."""
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        """Use gravatar avatars."""
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def get_reset_password_token(self, expires_in=600):
        """Generate token for password reset."""
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    # NOT IMPLEMENTED
    @staticmethod
    def verify_reset_password_token(token):
        """Verify password-reset token."""
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return Rater.query.get(id)


@login.user_loader
def load_user(id):
    """Load rater."""
    return Rater.query.get(int(id))


class Dataset(db.Model):
    """SQLAlchemy Model for Datasets (Set of Images)."""

    __searchable__ = ['name']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    images = db.relationship('Image', backref='dataset', lazy='dynamic')

    def __repr__(self):
        """Object representation."""
        return f'<Dataset {self.name}>'


class Image(db.Model):
    """SQLAlchemy Model for MRI."""

    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    path = db.Column(db.String(128), unique=True)
    extension = db.Column(db.String(8))
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    subject = db.Column(db.String(16))
    session = db.Column(db.String(16))
    ratings = db.relationship("Ratings", backref="image", lazy="dynamic")

    def __repr__(self):
        """Object representation."""
        return f'<MRImage {self.name}>'

    def set_rating(self, user, rating):
        """Set a rating to the current MRI."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            rating_mod = Ratings(rater=user, image=self, rating=rating)
            db.session.add(rating_mod)
            db.session.commit()
        else:
            rating_mod.rating = rating
            rating_mod.timestamp = datetime.utcnow()
            db.session.commit()

    def set_comment(self, user, comment):
        """Append a comment to the rating of current MRI."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            rating_mod = Ratings(rater=user, image=self, comment=comment)
            db.session.add(rating_mod)
            db.session.commit()
        else:
            rating_mod.comment = comment
            db.session.commit()

    def rating_by_user(self, user):
        """Return rating of the image by specific user."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            return 0
        return rating_mod.rating

    def comment_by_user(self, user):
        """Return rating of the image by specific user."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            return None
        return rating_mod.comment


class Ratings(db.Model):
    """SQLAlchemy Model for QC ratings."""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))

    def __repr__(self):
        """Object representation."""
        return f'<Rating {self.image_id}; {self.rating}>'
