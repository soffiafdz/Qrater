"""
Qrater.

Flask webapplication for QC Neuroimaging data.
IN DEVELOPMENT
"""

from app import create_app, db
from app.models import (Dataset, Rater, Image, Rating, History,
                        Notification, Task, Precomment)
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Pre-import models in shell context."""
    return {'db': db, 'Rater': Rater, 'Dataset': Dataset, 'Image': Image,
            'Rating': Rating,  "History": History,
            "Notification": Notification, "Task": Task,
            "Precomment": Precomment}
