"""
Main Blueprint: Forms.

Python module containing the 'forms' classes for the Main Blueprint.
"""

from flask_wtf import FlaskForm
from wtforms import (SubmitField, RadioField, SelectField, TextAreaField,
                     BooleanField)
from wtforms.validators import DataRequired, ValidationError


class EmptyForm(FlaskForm):
    """Empty form used for submission of ratings."""

    submit = SubmitField('Submit')


class RatingForm(FlaskForm):
    """Form for setting a rating/comment."""

    rating = RadioField('Rating', choices=[(0, 'Pending'), (1, 'Pass'),
                                           (2, 'Warning'), (3, 'Fail')])
    comment = TextAreaField('Comment')
    submit = SubmitField('Comment')


class ExportRatingsForm(FlaskForm):
    """Form for exporting the ratings."""

    file_type = RadioField("Format", choices=['CSV', 'JSON'],
                           validators=[DataRequired()])
    dataset = SelectField("Dataset", validators=[DataRequired()])
    rater_filter = RadioField("Rater(s)", choices=[(0, 'All Raters'),
                                                   (1, 'User')],
                              validators=[DataRequired()])
    # choices=[(0, current_user.username), (1, "All")])
    col_image = BooleanField("Image name")
    col_rater = BooleanField("Rater")
    col_sub = BooleanField("Subject")
    col_sess = BooleanField("Session")
    col_cohort = BooleanField("Cohort")
    col_comment = BooleanField("Comments")
    col_timestamp = BooleanField("Timestamp")

class ImportRatingsForm(FlaskForm):
    """Form for importing ratings."""

    file_type = RadioField("Format", choices=['CSV', 'JSON'],
                           validators=[DataRequired()])
    dataset = SelectField("Dataset", validators=[DataRequired()])
    col_image = BooleanField("Image name")
    col_rater = BooleanField("Rater")
    col_sub = BooleanField("Subject")
    col_sess = BooleanField("Session")
    col_cohort = BooleanField("Cohort")
    col_comment = BooleanField("Comments")
    col_timestamp = BooleanField("Timestamp")
