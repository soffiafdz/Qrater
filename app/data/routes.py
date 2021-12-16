"""
Qrater Data Management.

Module with blueprint specific routes
"""

import os
import re
from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import login_required, current_user
from app import db
from app.data import bp
from app.models import Dataset, Rater
from app.data.functions import load_data, upload_data
from app.data.forms import LoadDatasetForm, UploadDatasetForm, EditDatasetForm
from app.data.exceptions import (OrphanDatasetError, EmptyLoadError)


@bp.route('/upload-dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    data_dir = os.path.join(current_app.config['ABS_PATH'],
                            'static/datasets/uploaded')

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    form = UploadDatasetForm()
    if form.validate_on_submit():
        files = request.files.getlist(form.dataset.name)
        savedir = os.path.join(data_dir, form.dataset_name.data)

        # If savedir does not exist; create it
        if not os.path.isdir(savedir):
            os.makedirs(savedir)

        # Form checks that dataset does not exist already
        # so there is no need to check here; just create it
        dataset = Dataset(name=form.dataset_name.data,
                          creator=current_user,
                          private=form.privacy.data)
        dataset.grant_access(current_user)
        db.session.add(dataset)

        privacy = 'a PRIVATE' if dataset.private else 'an OPEN'
        flash(f"{dataset.name} was created as {privacy} dataset", 'info')

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

        return redirect(url_for('main.dashboard', all_raters=all_raters))
    for _, error in form.errors.items():
        flash(error[0], 'danger')
    return render_template('data/upload_dataset.html', form=form,
                           all_raters=all_raters, title='Upload Dataset')


@bp.route('/load-dataset', methods=['GET', 'POST'])
@bp.route('/load-dataset/<directory>', methods=['GET', 'POST'])
@login_required
def load_dataset(directory=None):
    """Page to load new datasets from within HOST."""
    data_dir = os.path.join(current_app.config['ABS_PATH'],
                            'static/datasets/preloaded')

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    # Choices of directories to load in form
    dir_choices = [d for d in os.listdir(data_dir)
                   if os.path.isdir(os.path.join(data_dir, d))]
    dir_choices.sort()

    info = {'directory': directory, 'new_imgs': 0}
    if directory is not None:
        # Save useful info for jinja template
        info['model'] = Dataset.query.filter_by(name=directory).first()
        # Check access before loading files
        if info['model']:
            info['access'] = current_user.has_access(info['model'])
            info['saved_imgs'] = info['model'].images.count()
        else:
            info['access'] = True
            info['saved_imgs'] = 0

        if info['access']:
            # Count the files in the directory
            all_files = []
            for root, _, files in os.walk(os.path.join(data_dir, directory)):
                all_files.extend([os.path.join(root, f)
                                  for f in files if not f.startswith('.')])
            info['new_imgs'] = len(all_files) - info['saved_imgs']

    form = LoadDatasetForm()
    form.dir_name.choices = dir_choices

    # Form submission must be restricted by access in template
    if form.validate_on_submit():
        if info['model']:
            new_dataset = False
        else:
            # If dataset is not a Dataset Model (does not exist), create it
            info['model'] = Dataset(name=form.dir_name.data,
                                    creator=current_user)
            db.session.add(info['model'])
            new_dataset = True
            flash(f"{info['model'].name} was created as an OPEN dataset",
                  'info')

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
                      'leaving the dataset empty', 'warning')

            else:
                if not new_dataset and loaded_imgs == 0:
                    flash('No new files were successfully loaded', 'warning')
                else:
                    flash(f'{loaded_imgs} file(s) successfully loaded!',
                          'success')
            finally:
                # Commit changes in database
                db.session.commit()

        return redirect(url_for('main.dashboard', all_raters=all_raters))

    # Form validation errors
    for _, error in form.errors.items():
        flash(error[0], 'danger')

    return render_template('data/load_dataset.html', form=form,
                           title="Load Dataset", dictionary=info,
                           all_raters=all_raters)


@bp.route('/edit-dataset', methods=['GET', 'POST'])
@bp.route('/edit-dataset/<dataset>', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset=None):
    """Page to edit an existing dataset of MRI."""
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    # Read-only; Disable dataset loader when accessing through link
    ro = request.args.get('ro', 0, type=int)

    ds_model = Dataset.query.\
        filter_by(name=dataset).\
        first_or_404() \
        if dataset else None

    form = EditDatasetForm()
    if ro:
        form.dataset.data = dataset

    privacy = ds_model.private if ds_model else None
    public_ds = Dataset.query.filter_by(private=False)
    private_ds = Dataset.query.filter(Dataset.viewers.contains(current_user))
    form.dataset.choices = [ds.name for ds in public_ds.union(private_ds)]
    form.viewers.choices = [(r.id, r.username, r in ds_model.viewers)
                            for r in Rater.query.order_by('username')
                            if r not in [current_user, ds_model.creator]] \
        if dataset else []

    # Test image names for regex helper
    test_names = {}
    for set in Dataset.query.all():
        test_names[set.name] = [img.path for img in set.images.limit(5).all()]

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
            # TODO: move to tasks
            for img in ds_model.images.all():
                # TODO Think about what to do if preloaded directory can't
                # change
                img.path = img.path.replace(ds_model.name, form.new_name.data)
                db.session.add(img)

            # Change dataset name in dataset database
            ds_model.name = form.new_name.data
            db.session.add(ds_model)
            changes = True

        # Regex for image type, cohort, subject and/or session
        # TODO: move to TASKS
        if form.sub_regex.data \
                or form.sess_regex.data \
                or form.type_regex.data \
                or form.cohort_regex.data:

            current_user.launch_task('edit_info',
                                     'Editing the info of '
                                     f"{ds_model.images.count()} images "
                                     f"from {ds_model.name} dataset",
                                     icon='edit', alert_color='primary',
                                     dataset_name=ds_model.name,
                                     sub_regex=form.sub_regex.data,
                                     sess_regex=form.sess_regex.data,
                                     cohort_regex=form.cohort_regex.data,
                                     type_regex=form.type_regex.data)
            db.session.commit()
            changes = True

        # Change privacy of dataset
        if ds_model.change_privacy(form.privacy.data):
            # Make sure current_user AND creator do not get kicked out
            ds_model.grant_access(ds_model.creator)
            ds_model.grant_access(current_user)
            db.session.commit()
            changes = True

        if form.privacy.data:
            orig_viewers = {rater.id for rater in ds_model.viewers}
            form_viewers = {r_id for r_id in form.viewers.data}

            for rater in [Rater.query.get(id)
                          for id in form_viewers - orig_viewers]:
                if ds_model.grant_access(rater):
                    changes = True

            for rater in [Rater.query.get(id)
                          for id in orig_viewers - form_viewers]:
                if ds_model.deny_access(rater):
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
                    changes = True

        if changes:
            flash(f'{ds_model.name} successfully edited!', 'success')
            db.session.commit()
            return redirect(url_for('main.dashboard', all_raters=all_raters))

    return render_template('data/edit_dataset.html', form=form,
                           dataset=dataset, privacy=privacy, ro=ro,
                           names=test_names, all_raters=all_raters,
                           title='Edit Dataset')


@bp.route('/delete-dataset/<dataset>')
@login_required
def delete_dataset(dataset):
    """Page to delete a dataset of MRI ratings."""
    # If dataset does not exit, throw 404
    ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')
    keep_imgs = request.args.get('keep_imgs', 0, type=int)
    remove_files = request.args.get('nuke', 0, type=int)
    all_raters = request.args.get('all_raters', 0, type=int)

    current_user.launch_task('delete_data',
                             'Deleting ratings and images from '
                             f'{dataset} dataset...',
                             icon='delete', alert_color='danger',
                             dataset_name=ds_model.name, data_dir=data_dir,
                             keep_imgs=keep_imgs, remove_files=remove_files)

    db.session.commit()

    return redirect(url_for('main.dashboard', all_raters=all_raters))
