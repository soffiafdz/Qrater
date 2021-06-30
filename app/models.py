"""
Qrater.

Global app module with Flask models.
"""

# MODIFY... What?
from datetime import datetime
from hashlib import md5
from time import time
import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import redis
import rq


class Rater(UserMixin, db.Model):
    """SQLALCHEMY Model of Raters (Users)."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    ratings = db.relationship("Rating", backref="rater", lazy="dynamic")
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')
    tasks = db.relationship('Task', backref='rater', lazy='dynamic')

    def __repr__(self):
        """Object representation."""
        return f'<Rater {self.username}>'

    def set_password(self, password):
        """Generate password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password validity."""
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        """Generate token for password reset."""
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        """Verify password-reset token."""
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return Rater.query.get(id)

    def add_notification(self, name, data):
        """Add a notification for this rater to the database."""
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        """Launch a task to the redis queue."""
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    rater=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        """Return complete list of rater's tasks currently in progress."""
        return Task.query.filter_by(rater=self, complete=False).all()

    def get_task_in_progress(self, name):
        """Return a single task by name currently in progress."""
        return Task.query.filter_by(name=name, rater=self,
                                    complete=False).first()

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
    imgtype = db.Column(db.String(16))
    ratings = db.relationship("Rating", backref="image", lazy="dynamic")

    def __repr__(self):
        """Object representation."""
        return f'<MRImage {self.name}>'

    def set_rating(self, user, rating):
        """Set a rating to the current MRI."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            rating_mod = Rating(rater=user, image=self, rating=rating)
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
            rating_mod = Rating(rater=user, image=self, comment=comment)
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


class Rating(db.Model):
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


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    """SQLAlchemy Model for background tasks."""

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        """Load a job instance."""
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """Return job progress."""
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100
