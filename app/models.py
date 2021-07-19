"""
Qrater.

Global app module with Flask models.
"""

from datetime import datetime
from time import time
import json
import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import redis
import rq


@login.user_loader
def load_user(id):
    """Load rater."""
    return Rater.query.get(int(id))


data_access = db.Table(
    'data_access',
    db.Column('rater_id', db.Integer, db.ForeignKey('rater.id')),
    db.Column('dataset_id', db.Integer, db.ForeignKey('dataset.id')),
)


class Rater(UserMixin, db.Model):
    """SQLALCHEMY Model of Raters (Users)."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.relationship("Rating", backref="rater", lazy="dynamic")
    datasets = db.relationship('Dataset', backref='creator', lazy='dynamic')
    tasks = db.relationship('Task', backref='rater', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')

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

    def has_access(self, dataset):
        """Query access permission to a dataset."""
        return dataset in self.access.all()

    def add_notification(self, name, data):
        """Add a notification for this rater to the database."""
        self.delete_notification(name)
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def delete_notification(self, name):
        """Delete a notification from this rater."""
        self.notifications.filter_by(name=name).delete()

    def launch_task(self, name, description, icon=None, alert_color=None,
                    *args, **kwargs):
        """Launch a task to the redis queue."""
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                                rater_id=self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    icon=icon, alert_color=alert_color, rater=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        """Return complete list of rater's tasks currently in progress."""
        return Task.query.filter_by(rater=self, complete=False).all()

    def get_task_in_progress(self, name):
        """Return a single task by name currently in progress."""
        return Task.query.filter_by(name=name, rater=self,
                                    complete=False).first()


class Dataset(db.Model):
    """SQLAlchemy Model for Datasets (Set of Images)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    private = db.Column(db.Boolean, default=False)
    images = db.relationship('Image', backref='dataset', lazy='dynamic')
    viewers = db.relationship('Rater', secondary=data_access,
                              backref='access', lazy='dynamic')

    def change_privacy(self, privacy):
        """Change the privacy status of the dataset."""
        if privacy != self.private:
            self.private = privacy
            return True
        return False

    def has_access(self, rater):
        """Query viewing access."""
        return rater in self.viewers.all()

    def grant_access(self, rater):
        """Grant viewing access to a non-creator rater."""
        if not self.has_access(rater):
            self.viewers.append(rater)
            return True
        return False

    def deny_access(self, rater):
        """Remove viewing access to a non-creator rater."""
        if rater != self.creator and self.has_access(rater):
            self.viewers.remove(rater)
            return True
        return False

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
    cohort = db.Column(db.String(16))
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
        else:
            rating_mod.rating = rating
            rating_mod.timestamp = datetime.utcnow()

    def set_comment(self, user, comment):
        """Append a comment to the rating of current MRI."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod is None:
            rating_mod = Rating(rater=user, image=self, comment=comment)
            db.session.add(rating_mod)
        else:
            rating_mod.comment = comment

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
    """SQLAlchemy Model for notifications."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    timestamp = db.Column(db.Float(precision=32), index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        """Return json from notification."""
        return json.loads(str(self.payload_json))


class Task(db.Model):
    """SQLAlchemy Model for background tasks."""

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    icon = db.Column(db.String(18))
    alert_color = db.Column(db.String(18))
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
