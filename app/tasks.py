"""
Qrater RQ Tasks.

Module for the background jobs of the webapp
"""

import sys
from rq import get_current_job
from flask import flash
from app import create_app, db
from app.models import Task
from app.data.functions import load_image
from app.data.exceptions import (NoExtensionError,
                                 UnsupportedExtensionError,
                                 OrphanDatasetError)

app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    """Set the progress of a task."""
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        # TODO: implement this somehow??
        task.rater.add_notification('task_progress',
                                    {'task_id': job.get_id(),
                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def load_data(files, savedir, dataset_model,
              img_model=None, host=False, new_dataset=False):
    """Start RQ task to upload dataset from client.

    Arguments:
        files       -- list of data files (CLIENT or HOST)
        directory   -- path (existing) where to save/link the images
        host        -- boolean for loading images within host
        dataset     -- dataset MODEL that the images pertain to
        img_model   -- image MODEL to check existance of data file
        new_dataset -- failsafe to avoid empty dataset in case of errors
    """
    try:
        # Init task and progress
        _set_task_progress(0)
        total_imgs = len(files)
        i = loaded_imgs = 0
        for img in files:
            # Check existance of file in directory (when HOST)
            # If uploading from browser (CLIENT), assume non-existance of file
            # (as new dataset must be created)
            existance = img_model.query.filter(
                img_model.name == img.rsplit('.', 1)[0],
                img_model.dataset == dataset_model
            ).first() if host else None

        if not existance:
            try:
                load_image(img, savedir, dataset_model, upload=host)

            except UnsupportedExtensionError:
                app.logger.error(f'Error in uploading {img}; unsupported ext',
                                 exc_info=sys.exc_info())

            except NoExtensionError:
                app.logger.error(f'Error in uploading {img}; no extension',
                                 exc_info=sys.exc_info())

            else:
                loaded_imgs += 1

            i += 1
            _set_task_progress(100 * i // total_imgs)

        if new_dataset and not loaded_imgs:
            raise OrphanDatasetError

    except OrphanDatasetError:
        app.logger.error(f'Error in uploading {dataset_model.name}; '
                         'orphaned; no images uploaded',
                         exc_info=sys.exc_info())
        db.session.delete(dataset_model)

    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

    else:
        flash(f'{loaded_imgs} file(s) successfully loaded!', 'success')

    finally:
        db.session.commit()
        _set_task_progress(100)
