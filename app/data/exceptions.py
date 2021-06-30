"""
Qrater Data Management.

Needed exceptions for uploading files
"""


class UnsupportedExtensionError(Exception):
    """Exception raised when file has non-implemented extension.

    Attributes:
        extension -- extension that caused the error
        message -- explanation of the error
    """

    def __init__(self, extension, message="Extension is not implemented"):
        """Initialize exception."""
        self.extension = extension
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """Express exception."""
        return f"{self.extension} -> {self.message}"


class NoExtensionError(Exception):
    """Exception raised when file has no extension (in filename).

    Attributes:
        filename -- filename that caused the error
        message -- explanation of the error
    """

    def __init__(self, filename, message="File has no declared extension"):
        """Initialize exception."""
        self.filename = filename
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """Express exception."""
        return f'{self.filename} -> {self.message}'


class OrphanDatasetError(Exception):
    """Exception raised when a dataset is created but left without images.

    Attributes:
        dataset -- name of dataset model orphaned
        message -- explanation of the error
    """

    def __init__(self, filename, message="Dataset model left empty"):
        """Initialize exception."""
        self.filename = filename
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """Express exception."""
        return f'{self.dataset} -> {self.message}'
