"""
Main Blueprint: Forms.

Python module containing the 'forms' classes for the Main Blueprint.
"""

from flask import request, current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField, MultipleFileField
from wtforms.validators import ValidationError, DataRequired, Length
# from app.models import User  # Rename to Rater


class UploadDatasetForm(FlaskForm):
    """Form for uploading a new dataset."""

    dataset_name = StringField("Dataset's name", validators=[DataRequired()])
    sub_regex = StringField("Subjects' label (regex)")
    sess_regex = StringField("Sessions' label (regex)")
    dataset = MultipleFileField('MRI files', validators=[DataRequired()])
    submit = SubmitField('Upload')


# ADAPT LATER
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
