"""
Qrater Uploads.

Needed functions for uploading files
"""

import os
from werkzeug.utils import secure_filename
from flask import current_app
from flask_login import current_user
from app import db
from app.models import Image


def load_image(image, directory, dataset, upload=False):
    """Load data of an image to an EXISTING dataset.

    Arguments:
        image: data file (CLIENT or HOST) of the image to load
        directory: path (existing) where to save/link the images
        dataset: dataset MODEL that the images pertain to
        upload: boolean to differentiate uploading vs linking (CLIENT v HOST)
    """

    filename = secure_filename(image.filename) \
        if upload else secure_filename(image)
    fpath = os.path.join(directory, filename)

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


def load_dataset(files, directory, dataset, img_model=None, host=False
                 quiet=False, new_dataset=False):
    """Load data of several images from CLIENT.

    Arguments:
        files: list of data files (CLIENT or HOST)
        directory: path (existing) where to save/link the images
        host: boolean for loading images within host
        dataset: dataset MODEL that the images pertain to
        img_model: image MODEL to check existance of data file
        quiet: boolean to inhibit flash in browser
        new_dataset: failsafe to avoid empty dataset in case of errors

    Returns: Number of successfully loaded images.
    """

    loaded_imgs = 0
    upload = False if host else True

    for img in files:
        # Check existence of file in directory when loading from host
        # if uploading from client, assume non-existance
        # (as new dataset is created)
        exists = model.query.filter(model.name == img.rsplit('.', 1)[0],
                                    model.dataset == dataset).first() \
            if host else None

        if not exists:
            try:
                load_image(img, directory, dataset, upload=upload)

            except UnsupportedExtensionError:
                app.logger.error(f'Error in uploading {img.filename}; '
                                 'unsupported ext', exc_info=sys.exc_info())
                if not quiet:
                    flash(f'{img.filename} is an unsupported filetype',
                          'danger')
                continue

            except NoExtensionError:
                app.logger.error(f'Error in uploading: {img.filename}; '
                                 'no extension', exc_info=sys.exc_info())
                if not quiet:
                    flash(f'{img.filename} does not have an extension',
                          'danger')
                continue

            else:
                loaded_imgs += 1

    if new_dataset and not loaded_imgs:
        raise OrphanDatasetError

    return loaded_imgs
