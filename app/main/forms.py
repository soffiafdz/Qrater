"""
Main Blueprint: Forms.

Python module containing the 'forms' classes for the Main Blueprint.
"""

from flask import request
from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, TextAreaField,
                     MultipleFileField, RadioField)
from wtforms.validators import DataRequired, Length


class UploadDatasetForm(FlaskForm):
    """Form for uploading a new dataset."""

    dataset_name = StringField("Dataset's name", validators=[DataRequired()])
    sub_regex = StringField("Subjects' label (regex)")
    sess_regex = StringField("Sessions' label (regex)")
    dataset = MultipleFileField('MRI files', validators=[DataRequired()])
    submit = SubmitField('Upload')


class EmptyForm(FlaskForm):
    """Empty form used for submission of ratings."""

    submit = SubmitField('Submit')


class RatingForm(FlaskForm):
    """Form for setting a rating/comment."""

    rating = RadioField('Rating', choices=[(0, 'Pending'),
                                           (1, 'Pass'),
                                           (2, 'Warning'),
                                           (3, 'Fail')])
    comment = StringField('Comment')
    submit = SubmitField('Comment')


# ADAPT LATER || DELETE???
class SearchForm(FlaskForm):
    """Search Form for Images in Database."""

    # NOT YET IMPLEMENTED
    q = StringField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        """Submit necessary values due to GET protocol."""
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super().__init__(*args, **kwargs)

# TODO: FORM FOR QC
# TODO: FORM FOR DATABASE ATTRIBUTES
