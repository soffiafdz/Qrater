"""
Qrater RQ Tasks.

Module for the background jobs of the webapp
"""

import sys
from rq import get_current_job
from flask import flash
from app import create_app, db
from app.models import Task, Image, Dataset
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


def load_data(files, dataset_name, new_dataset=False):
    """Start RQ task to upload dataset from client.

    Arguments:
        files           -- list of data files (HOST)
        dataset_name    -- dataset to which the images pertain to
        new_dataset     -- fail-safe to avoid empty dataset in case of errors
    """
    try:
        # Init task and progress
        _set_task_progress(0)
        total_imgs = len(files)
        i = loaded_imgs = 0
        dataset = Dataset.query.filter_by(name=dataset_name).first()

        for img in files:
            # Check existance of file
            filename = img.rsplit('/', 1)[-1]
            basename = filename.split('.', 1)[0]
            exists = Image.query.filter(
                Image.name == basename,
                Image.dataset == dataset
            ).first()

            if not exists:
                try:
                    load_image(img, dataset)
                except UnsupportedExtensionError:
                    app.logger.error(f'Error in uploading {img};'
                                     'unsupported ext',
                                     exc_info=sys.exc_info())
                except NoExtensionError:
                    app.logger.error(f'Error in uploading {img};'
                                     'no extension',
                                     exc_info=sys.exc_info())
                else:
                    loaded_imgs += 1
                    db.session.commit()

            i += 1
            _set_task_progress(100 * i // total_imgs)

        if new_dataset and not loaded_imgs:
            raise OrphanDatasetError

    except OrphanDatasetError:
        app.logger.error(f'Error in uploading {dataset.name}; '
                         'orphaned; no images uploaded',
                         exc_info=sys.exc_info())
        db.session.delete(dataset)

    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        db.session.rollback()

    finally:
        db.session.commit()
        _set_task_progress(100)
