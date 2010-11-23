from django.conf import settings
from django.core.validators import ValidationError

# A list of allowable thumbnail file extensions.
ALLOWABLE_THUMBNAIL_EXTENSIONS = getattr(settings, 
                                         'ALLOWABLE_THUMBNAIL_EXTENSIONS', 
                                         ['png', 'jpg', 'jpeg', 'gif'])

class ImageUploadExtensionValidator(object):
    """
    Perform some basic image uploading extension validation.
    """
    compare = lambda self, a, b: a is not b
    clean   = lambda self, x: x

    def __call__(self, value):
        filename = value.name
        filename_split = filename.split('.')
        extension = filename_split[-1]
        
        # Decided to require file extensions.
        if len(filename_split) < 2:
            raise ValidationError('Your file lacks an extension such as .jpg or .png. Please re-name it on your computer and re-upload it.',
                                  code='no_extension')

        # Restrict allowable extensions.
        if extension.lower() not in ALLOWABLE_THUMBNAIL_EXTENSIONS:
            # Format for your viewing pleasure.
            allowable_str = ' '.join(ALLOWABLE_THUMBNAIL_EXTENSIONS)
            raise ValidationError('Your file is not one of the allowable types: %s' % allowable_str,
                                  code='extension_not_allowed')