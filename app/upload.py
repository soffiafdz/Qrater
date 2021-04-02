"""
Qrater.

Needed functions for uploading files
"""


def allowed_file(filename, allowed_exts):
    """Check that the file is in."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in \
        allowed_exts
