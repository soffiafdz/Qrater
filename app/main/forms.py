"""
Main Blueprint: Forms.

Python module containing the 'forms' classes for the Main Blueprint.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (SubmitField, RadioField, SelectField, SelectMultipleField,
                     TextAreaField, StringField, IntegerField)
from wtforms.validators import DataRequired


class EmptyForm(FlaskForm):
    """Empty form used for submission of ratings."""

    submit = SubmitField('Submit')


class RatingForm(FlaskForm):
    """Form for setting a rating/comment."""

    rating = RadioField('Rating', choices=[(0, 'Pending'), (1, 'Pass'),
                                           (2, 'Warning'), (3, 'Fail')])
    subratings = StringField("Subratings")
    comment = TextAreaField('Comment')
    gotopage = IntegerField('Go-to Page')
    submit = SubmitField('Submit')


class ExportRatingsForm(FlaskForm):
    """Form for exporting the ratings."""

    file_type = RadioField("Format", choices=['CSV', 'JSON'],
                           validators=[DataRequired()])
    dataset = SelectField("Dataset", validators=[DataRequired()])
    rater_filter = RadioField("Rater(s)", choices=[(0, 'All Raters'),
                                                   (1, 'User')],
                              validators=[DataRequired()])
    history_filter = RadioField("History", choices=[(0, 'Current Rating'),
                                                   (1, 'Complete History')],
                              validators=[DataRequired()])
    # choices=[(0, current_user.username), (1, "All")])
    # Choices for this are stored in the route
    columns = SelectMultipleField("Columns", coerce=int)
    order = StringField("Order", validators=[DataRequired()])


class ImportRatingsForm(FlaskForm):
    """Form for importing ratings."""

    file_type = RadioField("Format", choices=['CSV', 'JSON'],
                           validators=[DataRequired()])
    dataset = SelectField("Dataset", validators=[DataRequired()])
    file = FileField("Ratings file",
                     validators=[FileRequired(), FileAllowed(['csv', 'json'])])
    # Choices for this are stored in the route
    columns = SelectMultipleField("Columns", coerce=int)
    order = StringField("Order", validators=[DataRequired()])
