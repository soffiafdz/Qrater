"""
Qrater Data Management.

Needed functions for uploading files
"""

import os
import sys
from werkzeug.utils import secure_filename
from flask import current_app, flash
from app import db
from app.models import Image
from app.data.exceptions import (NoExtensionError, OrphanDatasetError,
                                 UnsupportedExtensionError)


def load_image(image, savedir, dataset, upload=False):
    """Load data of an image to an EXISTING dataset.

    Arguments:
        image   -- data file (CLIENT or HOST) of the image to load
        savedir -- path (existing) where to save/link the images
        dataset -- dataset MODEL that the images pertain to
        upload  -- boolean to differentiate uploading vs linking (CLIENT/HOST)
    """
    file = image.filename if upload else image

    filename = secure_filename(file)
    fpath = os.path.join(savedir, filename)

    try:
        basename, extension = filename.split('.', 1)
        if extension.lower() in current_app.config['DSET_ALLOWED_EXTS']:
            if upload:
                image.save(fpath)  # Save file into savedir

            # Add Image to database
            db.session.add(Image(name=basename, path=fpath,
                                 extension=extension, dataset=dataset))

            # Should I delete this??
            # db.session.commit()
            # Commit database outside of function
        else:
            raise UnsupportedExtensionError(extension=extension)

    except ValueError:
        # File has no extension (Common in Linux)
        raise NoExtensionError(filename=filename)


def load_data(files, savedir, dataset, img_model=None, host=False,
              quiet=False, new_dataset=True):
    """Load data of several images from CLIENT.

    Arguments:
        files       -- list of data files (CLIENT or HOST)
        savedir     -- path (existing) where to save/link the images
        host        -- boolean for loading images within host
        dataset     -- dataset MODEL that the images pertain to
        img_model   -- image MODEL to check existance of data file
        quiet       -- boolean to inhibit flash in browser
        new_dataset -- failsafe to avoid empty dataset in case of errors

    Returns: Number of successfully loaded images.
    """
    loaded_imgs = 0
    for img in files:
        # Check existence of file in directory when loading from host
        # if uploading from client, assume non-existance
        # (as new dataset is created)
        exists = img_model.query.filter(
            img_model.name == img.rsplit('.', 1)[0],
            img_model.dataset == dataset).first() \
            if host else None

        upload = not host

        if not exists:
            try:
                load_image(img, savedir, dataset, upload=upload)

            except UnsupportedExtensionError:
                current_app.logger.error(f'Error in uploading {img.filename}; '
                                         'unsupported ext',
                                         exc_info=sys.exc_info())
                if not quiet:
                    flash(f'{img.filename} is an unsupported filetype',
                          'danger')

            except NoExtensionError:
                current_app.logger.error(f'Error in uploading {img.filename}; '
                                         'no extension',
                                         exc_info=sys.exc_info())
                if not quiet:
                    flash(f'{img.filename} does not have an extension',
                          'danger')

            else:
                loaded_imgs += 1

    if new_dataset and not loaded_imgs:
        raise OrphanDatasetError

    return loaded_imgs
