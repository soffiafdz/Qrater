"""
Qrater Data Management.

Module with blueprint specific Forms
"""

from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, MultipleFileField, SelectField,
                     SelectMultipleField, BooleanField)
from wtforms.validators import DataRequired, ValidationError
from app.models import Dataset


class LoadDatasetForm(FlaskForm):
    """Form for loading a new dataset from within host."""

    dir_name = SelectField("Directory", validators=[DataRequired()])
    submit = SubmitField('Load')


class UploadDatasetForm(FlaskForm):
    """Form for uploading a new dataset."""

    dataset_name = StringField("Dataset's name", validators=[DataRequired()])
    privacy = BooleanField("Private")
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
    privacy = BooleanField("Private")
    share_ratings = BooleanField("Sharing")
    # Choices for this will be generated in the route
    viewers = SelectMultipleField("Raters", coerce=int)
    sub_regex = StringField("Subjects' label (regex)")
    sess_regex = StringField("Sessions' label (regex)")
    cohort_regex = StringField("Cohort label (regex)")
    type_regex = StringField("Image type label (regex)")
    imgs_to_upload = MultipleFileField('MRI files')
    submit = SubmitField('Upload')
