"""
Qrater Uploads.

Module with blueprint specific routes
"""

# TODO Prune this list
import os
import re
import csv
import json
from shutil import rmtree
from collections import defaultdict
from datetime import datetime
from flask import (render_template, flash, abort, redirect, url_for, request,
                   current_app, send_file)
from flask_login import current_user, login_required
from app import db
from app.main.forms import (LoadDatasetForm, UploadDatasetForm,
                            EditDatasetForm, RatingForm, ExportRatingsForm)
from app.models import Dataset, Image, Rating, Rater
from app.main import bp

@bp.route('/upload-dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    form = UploadDatasetForm()
    if form.validate_on_submit():
        files = request.files.getlist(form.dataset.name)
        savedir = os.path.join(data_dir, form.dataset_name.data)

        # If savedir does not exist; create it
        if not os.path.isdir(savedir):
            os.makedirs(savedir)

        # Form checks that dataset does not exist already
        # so there is no need to check here; just create it
        dataset = Dataset(name=form.dataset_name.data)
        db.session.add(dataset)

        try:
            # Function returns number of uploaded images
            loaded_imgs = load_dataset(files, directory=savedir,
                                       dataset=dataset, new_dataset=True)
        except OrphanDatasetError:
            # If orphaned dataset, delete it
            db.session.delete(dataset)
        else:
            # If not, that means at least one image was uploaded
            # flash success with number of uploads
            flash(f'{loaded_imgs} file(s) successfully uploaded!', 'success')
        finally:
            # Commit changes in database
            db.session.commit()

        return redirect(url_for('main.dashboard'))
    for _, error in form.errors.items():
        flash(error[0], 'danger')
    return render_template('uploads/upload_dataset.html', form=form,
                           title='Upload Dataset')


@bp.route('/load-dataset', methods=['GET', 'POST'])
@bp.route('/load-dataset/<directory>', methods=['GET', 'POST'])
@login_required
def load_dataset(directory=None):
    """Page to load new datasets from within HOST."""
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    info = {'directory': directory, 'new_imgs': 0}
    if directory is not None:
        # Count the files in the directory
        num_files = 0
        for _, _, files in os.walk(os.path.join(data_dir, directory)):
            files[:] = [f for f in files
                        if not f.startswith('.')  # Omit dotfiles
                        and '.' in f]             # Omit files w/o extension

            # Count files of implemented filetypes
            num_files += len([f for f in files if f.split('.', 1)[1].lower()
                              in current_app.config['DSET_ALLOWED_EXTS']])

        # Save useful info for jinja template
        info['model'] = Dataset.query.filter_by(name=directory).first()
        info['saved_imgs'] = info['model'].images.count() \
            if info['model'] else 0
        info['new_imgs'] = num_files - info['saved_imgs']

    form = LoadDatasetForm()
    form.dir_name.choices = os.listdir(data_dir)
    if form.validate_on_submit():
        if info['model']:
            new_dataset = False
        else:
            # If dataset is not a Dataset Model (does not exist), create it
            info['model'] = Dataset(name=form.dir_name.data)
            db.session.add(info['model'])
            new_dataset = True
            # db.session.commit()

        # Loop through files
        # os.walk(path, followlinks=True) :: This would follow symlink location

        # TODO Test walk with links on BIC
        for root, _, files in \
                os.walk(os.path.join(data_dir, form.dir_name.data)):

            files[:] = [f for f in files
                        if not f.startswith('.')  # Omit dotfiles
                        and '.' in f]             # Omit files w/o extension

            try:
                # Function returns number of uploaded images
                loaded_imgs = load_dataset(files, directory=root,
                                           dataset=dataset, img_model=Image,
                                           host=True, new_dataset=new_dataset)
            except OrphanDatasetError:
                # If orphaned dataset, delete it
                db.session.delete(dataset)

            else:
                if not new_dataset and loaded_imgs == 0:
                    flash('No new files were successfully uploaded', 'info')
                else:
                    flash(f'{loaded_imgs} file(s) successfully uploaded!',
                          'success')
            finally:
                # Commit changes in database
                db.session.commit()

        return redirect(url_for('main.dashboard'))

    # Form validation errors
    for _, error in form.errors.items():
        flash(error[0], 'danger')

    return render_template('uploads/load_dataset.html', form=form,
                           title="Load Dataset", dict=info)


