"""
Main Blueprint: Forms.

Python module containing the 'forms' classes for the Main Blueprint.
"""

from flask import request
from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, MultipleFileField, RadioField,
                     SelectField, TextAreaField)
from wtforms.validators import DataRequired, ValidationError
from app.models import Dataset


class UploadDatasetForm(FlaskForm):
    """Form for uploading a new dataset."""

    dataset_name = StringField("Dataset's name", validators=[DataRequired()])
    dataset = MultipleFileField('MRI files', validators=[DataRequired()])
    submit = SubmitField('Upload')

    def validate_dataset_name(self, dataset_name):
        """Check that the dataset's name does not already exist."""
        ncheck = Dataset.query.filter_by(name=dataset_name.data).first()
        if ncheck is not None:
            raise ValidationError(
                f'A Dataset named "{ncheck.name}" already exists.')

class EditDatasetForm(FlaskForm):
    """Form for editing an existing dataset."""

    dataset = SelectField("Dataset", validators=[DataRequired()])
    new_name = StringField("Dataset's name")
    sub_regex = StringField("Subjects' label (regex)")
    sess_regex = StringField("Sessions' label (regex)")
    imgs_to_upload = MultipleFileField('MRI files')
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
    comment = TextAreaField('Comment')
    submit = SubmitField('Comment')

# TODO: FORM FOR QC
# TODO: FORM FOR DATABASE ATTRIBUTES
