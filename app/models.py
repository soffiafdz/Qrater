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
from sqlalchemy.ext.hybrid import hybrid_property
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


subrating = db.Table(
    'subrating',
    db.Column('rating_id', db.Integer, db.ForeignKey('rating.id')),
    db.Column('precomment_id', db.Integer, db.ForeignKey('precomment.id'))
)


subrating_history = db.Table(
    'subrating_history',
    db.Column('history_id', db.Integer, db.ForeignKey('history.id')),
    db.Column('precomment_id', db.Integer, db.ForeignKey('precomment.id'))
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
        return not dataset.private or dataset in self.access

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
    sharing = db.Column(db.Boolean, default=True)
    images = db.relationship('Image', backref='dataset', lazy='dynamic')
    subratings = db.relationship('Precomment', backref='dataset',
                                 lazy='dynamic')
    viewers = db.relationship('Rater', secondary=data_access,
                              backref='access', lazy='dynamic')

    def change_privacy(self, privacy):
        """Change the privacy status of the dataset."""
        if privacy != self.private:
            self.private = privacy
            return True
        return False

    def change_sharing(self, sharing):
        """Change the sharing status of the dataset."""
        if sharing != self.sharing:
            self.sharing = sharing
            return True
        return False

    def has_access(self, rater):
        """Query viewing access."""
        return rater in self.viewers or not self.private

    def grant_access(self, rater):
        """Grant viewing access to a non-creator rater."""
        if not self.has_access(rater):
            self.viewers.append(rater)
            return True
        return False

    def deny_access(self, rater, force=False):
        """Remove viewing access to a non-creator rater."""
        if (rater != self.creator or force) and self.has_access(rater):
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

    def set_rating(self, user, rating=None, comment=None, timestamp=None):
        """Set a rating to the current Image and save to history."""
        if isinstance(timestamp, str):
            new_time = datetime.fromisoformat(timestamp[:-1]) \
                if timestamp[-1].isalpha() \
                else datetime.fromisoformat(timestamp)
        else:
            new_time = timestamp

        rating_mod = self.ratings.filter_by(rater=user).first()

        if rating_mod:
            rating_mod.save()
            # Update values if not None else existing/default
            rating_mod.rating = rating if rating else rating_mod.rating
            rating_mod.comment = comment if comment else rating_mod.comment
            rating_mod.timestamp = new_time if new_time else datetime.utcnow()
        else:
            rating_mod = Rating(rater=user, image=self,
                                rating=rating, comment=comment,
                                timestamp=new_time)
            db.session.add(rating_mod)
            rating_mod.save()

    def rating_by_user(self, user):
        """Return rating of the image by specific user."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod:
            return rating_mod.rating
        return 0

    def comment_by_user(self, user, add_subratings=True):
        """Return comment(s) of the image by specific user."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod:
            output = comment = rating_mod.comment
            if add_subratings:
                subratings = ", ".join(
                    [subr.comment for subr in rating_mod.subratings])

                output = "; ".join([subratings, comment]) \
                    if subratings else output
            return output
        return ""

    def subratings_by_user(self, user):
        """Return list of subratings of the image by specific user."""
        rating_mod = self.ratings.filter_by(rater=user).first()
        if rating_mod:
            return rating_mod.subratings
        return []


class Rating(db.Model):
    """SQLAlchemy Model for QC ratings."""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    rater_id = db.Column(db.Integer, db.ForeignKey('rater.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))
    history = db.relationship("History", backref='latest', lazy='dynamic')
    subratings = db.relationship('Precomment', secondary=subrating,
                                 backref='reference', lazy='dynamic')

    def __repr__(self):
        """Object representation."""
        return f'<Rating {self.image_id}; {self.rating}>'

    def save(self):
        """Save rating in history table."""
        n = self.history.count() + 1
        entry = History(latest=self, rating=self.rating, n=n,
                        comment=self.comment, timestamp=self.timestamp,
                        subratings=self.subratings)
        db.session.add(entry)

    def subrating(self, subrating, action="toggle"):
        """Toggle/Add/Remove subrating to current rating."""
        if not isinstance(subrating, Precomment):
            return False

        if action == "toggle":
            if subrating in self.subratings:
                action = "remove"
            else:
                action = "add"

        if action == "add":
            subrating in self.subratings or self.subratings.append(subrating)

        elif action == "remove":
            subrating in self.subratings and self.subratings.remove(subrating)

        else:
            return False

        return True


class Precomment(db.Model):
    """SQLAlchemy Model for QC subrating."""

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    rating = db.Column(db.Integer, default=0)
    comment = db.Column(db.String(256))
    keybinding = db.Column(db.String(3))

    def __repr__(self):
        """Object representation."""
        return f'<Subrating {self.dataset}; {self.comment}>'


class History(db.Model):
    """SQLAlchemy Model for history of QC ratings."""

    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey('rating.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    n = db.Column(db.Integer)
    subratings = db.relationship('Precomment', secondary=subrating_history,
                                 backref='history', lazy='dynamic')

    def __repr__(self):
        """Object representation."""
        return f'<Rating {self.latest}; {self.n}>'


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
