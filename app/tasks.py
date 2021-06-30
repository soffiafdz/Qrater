import sys
from rq import get_current_job
from app import create_app, db
from app.models import Task

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


def upload_dataset(files, savedir, dataset_name):
    """Start RQ task to upload dataset from client."""
    try:
        dataset = Dataset(name=dataset_name)

        pass
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)


def load_dataset():
    try:
        pass
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)


def export_ratings():
    try:
        pass
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)
