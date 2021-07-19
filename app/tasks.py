"""
Qrater RQ Tasks.

Module for the background jobs of the webapp
"""

import sys
import os
import re
from shutil import rmtree
from rq import get_current_job
from app import create_app, db
from app.models import Task, Dataset, Rater
from app.data.functions import load_image
from app.data.exceptions import (NoExtensionError,
                                 UnsupportedExtensionError,
                                 OrphanDatasetError,
                                 DuplicateImageError)

app = create_app()
app.app_context().push()


def _set_task_progress(progress, name='task_progress'):
    """Set the progress of a task."""
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.rater.add_notification(name,
                                    {'task_id': job.get_id(),
                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def load_data(files, dataset_name, rater_id,
              new_dataset=False, ignore_existing=False):
    """Start RQ task to upload dataset from client.

    Arguments:
        files           -- list of data files (HOST)
        dataset_name    -- dataset to which the images pertain to
        new_dataset     -- fail-safe to avoid empty dataset in case of errors
        ignore_existing -- Don't throw error when parsing existing files
    """
    try:
        # Init task and progress
        _set_task_progress(0, name=f'load_progress_{dataset_name}')
        total_imgs = len(files)
        i = loaded_imgs = 0
        dataset = Dataset.query.filter_by(name=dataset_name).first()
        rater = Rater.query.get(rater_id)

        for img in files:
            try:
                load_image(img, dataset)

            except UnsupportedExtensionError as error:
                rater.add_notification('load_alert',
                                       {'icon': '#exclamation-triangle-fill',
                                        'color': 'danger',
                                        'message': str(error)})
                continue

            except NoExtensionError as error:
                rater.add_notification('load_alert',
                                       {'icon': '#exclamation-triangle-fill',
                                        'color': 'danger',
                                        'message': str(error)})
                continue

            except DuplicateImageError as error:
                if not ignore_existing:
                    rater.add_notification('load_alert', {
                        'icon': '#exclamation-triangle-fill',
                        'color': 'danger',
                        'message': str(error)})
                continue

            else:
                loaded_imgs += 1

            i += 1
            _set_task_progress(100 * i // total_imgs,
                               name=f'load_progress_{dataset_name}')

        if new_dataset and not loaded_imgs:
            raise OrphanDatasetError(dataset_name)

    except OrphanDatasetError as error:
        rater.add_notification('load_alert',
                               {'icon': '#exclamation-triangle-fill',
                                'color': 'warning',
                                'message': str(error)})

    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        db.session.rollback()

    else:
        rater.add_notification('load_alert',
                               {'icon': '#check-circle-fill',
                                'color': 'success',
                                'message':
                                f'{loaded_imgs} file(s) successfully loaded!'})

    finally:
        db.session.commit()
        _set_task_progress(100, name=f'load_progress_{dataset_name}')


def edit_info(dataset_name, rater_id, sub_regex=None, sess_regex=None,
              cohort_regex=None, type_regex=None):
    """Start RQ task to edit a dataset.

    Arguments:
        dataset_name    -- dataset to edit
        sub_regex       -- regular expression from edit-form
        sess_regex      -- regular expression from edit-form
        cohort_regex    -- regular expression from edit-form
        type_regex      -- regular expression from edit-form
    """
    try:
        _set_task_progress(0, name=f'edit_progress_{dataset_name}')
        dataset = Dataset.query.filter_by(name=dataset_name).first()
        rater = Rater.query.get(rater_id)
        i = 0
        changed_imgs = 0

        for image in dataset.images.all():
            change = False
            if sub_regex:
                pattern = sub_regex
                result = re.search(pattern, image.path)
                if result:
                    image.subject = result.group()
                    change = True
            if sess_regex:
                pattern = sess_regex
                result = re.search(pattern, image.path)
                if result:
                    image.session = result.group()
                    change = True
            if cohort_regex:
                pattern = cohort_regex
                result = re.search(pattern, image.path)
                if result:
                    image.cohort = result.group()
                    change = True
            if type_regex:
                pattern = type_regex
                result = re.search(pattern, image.path)
                if result:
                    image.imgtype = result.group()
                    change = True
            if change:
                changed_imgs += 1
                db.session.add(image)

            i += 1
            _set_task_progress(100 * i // dataset.images.count(),
                               name=f'edit_progress_{dataset_name}')

    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        db.session.rollback()

    else:
        if changed_imgs > 0:
            rater.add_notification('edit_alert',
                                   {'icon': '#check-circle-fill',
                                    'color': 'success',
                                    'message':
                                    f'Information of {changed_imgs} images'
                                    f'from {dataset_name} was successfully'
                                    'added!'})
        else:
            rater.add_notification('edit_alert',
                                   {'icon': '#exclamation-triangle-fill',
                                    'color': 'warning',
                                    'message':
                                    'No new information was added to the'
                                    'images of {dataset_name}...'})

    finally:
        db.session.commit()
        _set_task_progress(100, name=f'edit_progress_{dataset_name}')


def delete_data(dataset_name, data_dir, rater_id, remove_files=False):
    """Start RQ task to delete a dataset.

    Arguments:
        dataset_name    -- dataset to delete
        data_dir        -- directory where data is located
        remove_files    -- delete files
    """
    try:
        # Init task and progress
        _set_task_progress(0, name=f'delete_progress_{dataset_name}')
        dataset = Dataset.query.filter_by(name=dataset_name).first()
        rater = Rater.query.get(rater_id)
        i = 0
        end = len(dataset.images.all()) * 2 \
            if remove_files else len(dataset.images.all())

        for image in dataset.images.all():
            for rating in image.ratings.all():
                db.session.delete(rating)       # Delete ratings
            db.session.delete(image)            # Remove image from database
            i += 1
            _set_task_progress(100 * i // end,
                               name=f'delete_progress_{dataset_name}')

        if remove_files:
            ds_dir = os.path.join(data_dir, 'uploaded', dataset_name)
            if os.path.exists(ds_dir):
                rmtree(ds_dir)

        db.session.delete(dataset)

    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        db.session.rollback()

    else:
        rater.add_notification('delete_alert',
                               {'icon': '#check-circle-fill',
                                'color': 'success',
                                'message':
                                f'{dataset_name} successfully deleted!'})

    finally:
        db.session.commit()
        _set_task_progress(100, name=f'delete_progress_{dataset_name}')
