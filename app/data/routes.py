"""
Qrater Data Management.

Module with blueprint specific routes
"""

import os
import re
from time import time
from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import login_required, current_user
from app import db
from app.data import bp
from app.models import Dataset
from app.data.functions import load_data, upload_data
from app.data.forms import LoadDatasetForm, UploadDatasetForm, EditDatasetForm
from app.data.exceptions import (OrphanDatasetError, EmptyLoadError)


@bp.route('/upload-dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    data_dir = os.path.join(current_app.config['ABS_PATH'],
                            'static/datasets/uploaded')

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

        if len(files) > 10:
            # Redis can't handle FileStorage
            # First upload all files
            files_uploaded = upload_data(files, savedir)
            current_user.launch_task('load_data',
                                     f'Uploading {len(files)} new images '
                                     f'to {dataset.name} dataset...',
                                     icon='upload',
                                     alert_color='primary',
                                     files=files_uploaded,
                                     dataset_name=dataset.name,
                                     new_dataset=True)
            db.session.commit()
        else:
            try:
                # Function returns number of uploaded images
                loaded_imgs = load_data(files, dataset, savedir=savedir)
            except OrphanDatasetError:
                # If orphaned dataset, delete it
                db.session.delete(dataset)
            else:
                # If not, that means at least one image was uploaded
                # flash success with number of uploads
                flash(f'{loaded_imgs} file(s) successfully loaded!', 'success')
            finally:
                # Commit changes in database
                db.session.commit()

        return redirect(url_for('main.dashboard'))
    for _, error in form.errors.items():
        flash(error[0], 'danger')
    return render_template('data/upload_dataset.html', form=form,
                           title='Upload Dataset')


@bp.route('/load-dataset', methods=['GET', 'POST'])
@bp.route('/load-dataset/<directory>', methods=['GET', 'POST'])
@login_required
def load_dataset(directory=None):
    """Page to load new datasets from within HOST."""
    data_dir = os.path.join(current_app.config['ABS_PATH'],
                            'static/datasets/preloaded')

    # Choices of directories to load in form
    dir_choices = [d for d in os.listdir(data_dir)
                   if os.path.isdir(os.path.join(data_dir, d))]

    info = {'directory': directory, 'new_imgs': 0}
    if directory is not None:
        # Count the files in the directory
        all_files= []
        for root, _, files in os.walk(os.path.join(data_dir, directory)):
            all_files.extend([f for f in files if not f.startswith('.')])
            # files[:] = [f for f in files
                        # if not f.startswith('.')  # Omit dotfiles
                        # and '.' in f]             # Omit files w/o extension

        # Save useful info for jinja template
        info['model'] = Dataset.query.filter_by(name=directory).first()
        info['saved_imgs'] = info['model'].images.count() \
            if info['model'] else 0
        info['new_imgs'] = len(all_files) - info['saved_imgs']

    form = LoadDatasetForm()
    form.dir_name.choices = dir_choices
    if form.validate_on_submit():
        if info['model']:
            new_dataset = False
        else:
            # If dataset is not a Dataset Model (does not exist), create it
            info['model'] = Dataset(name=form.dir_name.data)
            db.session.add(info['model'])
            new_dataset = True

        if len(all_files) > 10:
            current_user.launch_task('load_data',
                                     f"Loading {info['new_imgs']} new images "
                                     f"to {info['model'].name} dataset...",
                                     icon='load',
                                     alert_color='primary',
                                     files=all_files,
                                     dataset_name=info['model'].name,
                                     new_dataset=new_dataset,
                                     ignore_existing=True)
            db.session.commit()
        else:
            try:
                # Function returns number of uploaded images
                loaded_imgs = load_data(all_files, dataset=info['model'],
                                        host=True, new_dataset=new_dataset)

            except OrphanDatasetError:
                # If orphaned dataset, delete it
                # TODO this somehow throws an error; look into this
                # db.session.delete(info['model'])
                flash('No new files were successfully loaded '
                      'leaving the dataset empty', 'danger')

            else:
                if not new_dataset and loaded_imgs == 0:
                    flash('No new files were successfully loaded', 'info')
                else:
                    flash(f'{loaded_imgs} file(s) successfully loaded!',
                          'success')
            finally:
                # Commit changes in database
                db.session.commit()

        return redirect(url_for('main.dashboard'))

    # Form validation errors
    for _, error in form.errors.items():
        flash(error[0], 'danger')

    return render_template('data/load_dataset.html', form=form,
                           title="Load Dataset", dict=info)


@bp.route('/edit-dataset', methods=['GET', 'POST'])
@bp.route('/edit-dataset/<dataset>', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset=None):
    """Page to edit an existing dataset of MRI."""
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()

    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    form = EditDatasetForm()
    form.dataset.choices = [ds.name for ds in Dataset.query.order_by('name')]

    # Test image names for regex helper
    test_names = {}
    for set in Dataset.query.all():
        test_names[set.name] = [img.name for img in set.images.limit(5).all()]

    changes = False
    if form.validate_on_submit():

        # Check if there is a name change;
        if form.new_name.data and form.new_name.data != ds_model.name:

            # If there is another dataset with that name, throw error
            if Dataset.query.filter_by(name=form.new_name.data).first():
                flash((f'A Dataset named "{form.new_name.data}" '
                      'already exists. Please choose another name'),
                      'danger')
                return redirect(request.url)

            # Rename dataset directory
            for d in ['preloaded', 'uploaded']:
                old_dir = os.path.join(data_dir, d, ds_model.name)
                new_dir = os.path.join(data_dir, d, form.new_name.data)
                if os.path.isdir(old_dir):
                    # TODO Include try/exception for writing permissions
                    os.rename(old_dir, new_dir)

            # Change dataset name in images database
            for img in ds_model.images.all():
                # TODO Think about what to do if preloaded directory can't
                # change
                img.path = img.path.replace(ds_model.name, form.new_name.data)
                db.session.add(img)

            # Change dataset name in dataset database
            ds_model.name = form.new_name.data
            db.session.add(ds_model)

            # Save database changes
            db.session.commit()
            changes = True

        files = request.files.getlist(form.imgs_to_upload.name)

        # Check that files is not an empty list??
        # Maybe to trigger upload
        if files[0].filename != "":
            savedir = os.path.join(data_dir, 'uploaded', ds_model.name)

            if len(files) > 10:
                # Redis can't handle FileStorage
                # First upload all files
                files_uploaded = upload_data(files, savedir)
                current_user.launch_task('load_data',
                                         f'Uploading {len(files)} new images '
                                         f'to {ds_model.name} dataset...',
                                         icon='upload',
                                         alert_color='primary',
                                         files=files_uploaded,
                                         dataset_name=ds_model.name)
                db.session.commit()
                changes = True
            else:
                try:
                    # Function returns number of uploaded images
                    loaded_imgs = load_data(files, savedir=savedir,
                                            dataset=ds_model,
                                            new_dataset=False)

                except EmptyLoadError as error:
                    flash(str(error), 'warning')

                except OrphanDatasetError as error:
                    flash(str(error), 'warning')

                else:
                    flash(f'{loaded_imgs} file(s) successfully uploaded!',
                          'success')
                    db.session.commit()
                    changes = True

        # Regex for image type, subject and/or session
        if form.sub_regex.data \
                or form.sess_regex.data \
                or form.type_regex.data:
            for img in ds_model.images.all():
                img_change = False
                if form.sub_regex.data:
                    pattern = form.sub_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.subject = result.group()
                        img_change = True
                if form.sess_regex.data:
                    pattern = form.sess_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.session = result.group()
                        img_change = True
                if form.type_regex.data:
                    pattern = form.type_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.imgtype = result.group()
                        img_change = True
                if img_change:
                    db.session.add(img)
                    db.session.commit()
            changes = True

        if changes:
            flash(f'{ds_model.name} successfully edited!', 'success')
            return redirect(url_for('main.dashboard'))

    return render_template('data/edit_dataset.html', form=form,
                           dataset=dataset, names=test_names,
                           title='Edit Dataset')


@bp.route('/delete-dataset/<dataset>')
@login_required
def delete_dataset(dataset):
    """Page to delete a dataset of MRI ratings."""
    # If dataset does not exit, throw 404
    ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')
    remove_files = request.args.get('nuke', 0, type=int)

    current_user.launch_task('delete_data',
                             'Deleting ratings and images from '
                             f'{dataset} dataset...',
                             icon='delete',
                             alert_color='danger',
                             dataset_name=ds_model.name,
                             data_dir=data_dir,
                             remove_files=remove_files)

    db.session.commit()

    return redirect(url_for('main.dashboard'))
