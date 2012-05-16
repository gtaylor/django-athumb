"""
Some top-level exceptions that are generally useful.
"""
class UploadedImageIsUnreadableError(Exception):
    """
    Raise this when the image generation backend can't read the image being
    uploaded. This doesn't necessarily mean that the image is definitely
    mal-formed or corrupt, but the imaging library (as it is compiled) can't
    read it.
    """
    pass