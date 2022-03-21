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
                                 UnsupportedExtensionError,
                                 DuplicateImageError, EmptyLoadError)


def upload_data(files, savedir):
    """Upload all data to be sorted later.

    Arguments:
        files   -- list of FileStorage objects to be *quickly* uploaded
        savedir -- path (existing) where to save the images

    Returns:
        list of file paths
    """
    list_files = []
    for f in files:
        filename = secure_filename(f.filename)
        fpath = os.path.join(savedir, filename)
        f.save(fpath)
        list_files.append(fpath)
    return list_files


def upload_file(file, savedir, valid_extensions=None):
    """Upload single file to be sorted later.

    Arguments:
        file                -- FileStorage object to be uploaded
        savedir             -- path (existing) where to save file
        valid_extensions    -- list with valid extensions (optional)

    Returns:
        String with path to saved file
    """
    filename = secure_filename(file.filename)
    fpath = os.path.join(savedir, filename)
    file.save(fpath)

    valid_extensions = valid_extensions if valid_extensions \
        else current_app.config['DSET_ALLOWED_EXTS']
    try:
        basename, extension = filename.split('.', 1)
        if extension.lower() not in valid_extensions:
            raise UnsupportedExtensionError(extension=extension)

    except ValueError:
        # File has no extension (Common in Linux)
        raise NoExtensionError(filename=filename)

    return(fpath)


def load_image(image, dataset):
    """Load data of an image to an EXISTING dataset.

    Arguments:
        image   -- path to data file (HOST) of the image to load
        dataset -- dataset MODEL that the images pertain to
    """
    filename = image.rsplit('/', 1)[-1]
    try:
        basename, extension = filename.split('.', 1)
        if extension.lower() not in current_app.config['DSET_ALLOWED_EXTS']:
            raise UnsupportedExtensionError(extension=extension)

        if Image.query.filter(
            Image.name == basename,
            Image.dataset == dataset
        ).first():
            raise DuplicateImageError(basename)

        # Add Image to database
        db.session.add(Image(name=basename, path=image,
                             extension=extension, dataset=dataset))

    except ValueError:
        # File has no extension (Common in Linux)
        raise NoExtensionError(filename=image)


def load_data(files, dataset, savedir=None, host=False, quiet=False,
              new_dataset=True):
    """Load data of several images from CLIENT.

    Arguments:
        files       -- list of data files (CLIENT or HOST)
        dataset     -- dataset MODEL that the images pertain to
        host        -- boolean for loading images within host
        savedir     -- path (existing) where to save the images
        quiet       -- boolean to inhibit flash in browser
        new_dataset -- failsafe to avoid empty dataset in case of errors

    Returns: Number of successfully loaded images.
    """
    # First upload all files
    if not host:
        files = upload_data(files, savedir)

    loaded_imgs = 0
    for img in files:
        try:
            load_image(img, dataset)

        except UnsupportedExtensionError as error:
            # current_app.logger.error(error, exc_info=sys.exc_info())
            if not quiet:
                flash(str(error), 'danger')
            else:
                pass

        except NoExtensionError as error:
            # current_app.logger.error(error, exc_info=sys.exc_info())
            if not quiet:
                flash(str(error), 'danger')
            else:
                pass

        except DuplicateImageError as error:
            # current_app.logger.error(error, exc_info=sys.exc_info())
            if not quiet:
                flash(str(error), 'danger')
            else:
                pass

        else:
            loaded_imgs += 1

    if not loaded_imgs:
        if new_dataset:
            raise OrphanDatasetError(dataset.name)
        else:
            raise EmptyLoadError

    return loaded_imgs
