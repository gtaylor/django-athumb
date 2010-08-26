# -*- encoding: utf-8 -*-
"""
Thumbnailing model fields. Plays nicely with Django storage backends, most
notably S3. Pre-generates thumbnails based on the sizes specified on the 
models. 

90% original, but the thumbnailing PIL generate_thumb() method provided by: 

django-thumbs by Antonio Melé
http://django.es
"""
import os
import cStringIO
import re

from PIL import Image
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile
from django.core.files.base import ContentFile
from django.core.validators import ValidationError
from django.conf import settings
from django.core.cache import cache

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
        if extension.lower() not in settings.ALLOWABLE_THUMBNAIL_EXTENSIONS:
            # Format for your viewing pleasure.
            allowable_str = ' '.join(settings.ALLOWABLE_THUMBNAIL_EXTENSIONS)
            raise ValidationError('Your file is not one of the allowable types: %s' % allowable_str,
                                  code='extension_not_allowed')
# Models want this instantiated ahead of time.
image_extension_validator = ImageUploadExtensionValidator()

def generate_thumb(orig_image, thumb_size, format):
    """
    Generates a thumbnail image and returns a ContentFile object with the thumbnail
    
    Parameters:
    ===========
    orig         A PIL Image object to thumbnail.
    
    thumb_size  desired thumbnail size, ie: (200,120)
    
    format      format of the original image ('jpeg','gif','png',...)
                (this format will be used for the generated thumbnail, too)
    """
    image = orig_image.copy()
    # get size
    thumb_w, thumb_h = thumb_size
    # If you want to generate a square thumbnail
    if thumb_w == thumb_h:
        # quad
        xsize, ysize = image.size
        # get minimum size
        minsize = min(xsize,ysize)
        # largest square possible in the image
        xnewsize = (xsize-minsize)/2
        ynewsize = (ysize-minsize)/2
        # crop it
        image2 = image.crop((xnewsize, ynewsize, xsize-xnewsize, ysize-ynewsize))
        # load is necessary after crop                
        image2.load()
        # thumbnail of the cropped image (with ANTIALIAS to make it look better)
        image2.thumbnail(thumb_size, Image.ANTIALIAS)
    else:
        # not quad
        image2 = image
        image2.thumbnail(thumb_size, Image.ANTIALIAS)
    
    io = cStringIO.StringIO()
    # PNG and GIF are the same, JPG is JPEG
    if format.upper() == 'JPG':
        format = 'JPEG'
    
    image2.save(io, format)
    return ContentFile(io.getvalue())    

class ImageWithThumbsFieldFile(ImageFieldFile):
    """
    Serves as the file-level storage object for thumbnails.
    """
    def __getattr__(self, name):
        """
        This is used to retrieve thumbnail URLs. See ImageWithThumbsField for 
        usage example. For example, when you do something like this from a 
        template:
    
        my_object.photo.url_125x125
        
        The URL string for the thumbnail of that dimension will be returned.
        
        WARNING: NO error checking is performed when asking for a certain
        dimension. This would be time-consuming for the S3 backend.
        
        TODO: Check the dimensions against the 'sizes' attribute and either warn
        or raise an exception.
        
        name: (str) The attribute that couldn't be found so far.
        """
        # Check to see if this is a imagefield.url_NxN call.
        thumb_regexp = re.compile('url_(?P<thumb_width>\d+)x(?P<thumb_height>\d+)')
        matches = thumb_regexp.match(name)

        if not matches:
            # This really is an invalid attribute call. Raise.
            raise AttributeError()
            
        thumb_width = int(matches.group('thumb_width')) 
        thumb_height = int(matches.group('thumb_height'))
                
        # Try to see if we can hit the cache instead of asking the storage
        # backend for the URL. This is particularly important for S3 backends.
        try:
            cache_key = "Thumbcache_%s_%dx%d" % (self.url, thumb_width, thumb_height)
        except ValueError:
            # If there's no file associated with this field, just die.
            # Trying to access self.url raises this.
            raise AttributeError()

        cached_val = cache.get(cache_key)
        if cached_val:
            return cached_val
        
        # Split URL from GET attribs.
        url_get_split = self.url.rsplit('?', 1)
        # Just the URL string (no GET attribs).
        url_str = url_get_split[0]
        
        # Get the URL string without the original's filename at the end.
        url_minus_filename = url_str.rsplit('/', 1)[0]
        
        # Determine what the filename would be for a thumb with these
        # dimensions, regardless of whether it actually exists.
        new_filename = self._calc_thumb_size_filename((thumb_width, thumb_height))
        
        # Slap the new thumbnail filename on the end of the old URL, in place
        # of the orignal image's filename.
        new_url = "%s/%s?cbust=%s" % (url_minus_filename, 
                                      os.path.basename(new_filename),
                                      settings.MEDIA_CACHE_BUSTER)
        # Cache this so we don't have to hit the storage backend for a while.
        cache.set(cache_key, new_url, settings.THUMBNAIL_URL_CACHE_TIME)
        return new_url
        
    def get_thumbnail_format(self):
        """
        Determines the target thumbnail type either by looking for a format
        override specified at the model level, or by using the format the
        user uploaded.
        """
        if self.field.thumbnail_format:
            # Over-ride was given, use that instead.
            return self.field.thumbnail_format.lower()
        else:
            # Use the existing extension from the file.
            filename_split = self.name.rsplit('.',1)
            return filename_split[-1]
                
    def save(self, name, content, save=True):
        """
        Handles some extra logic to generate the thumbnails when the original
        file is uploaded.
        """
        super(ImageWithThumbsFieldFile, self).save(name, content, save)
        
        # see http://code.djangoproject.com/ticket/8222 for details
        content.seek(0)
        image = Image.open(content)
        
        # Convert to RGBA (alpha) if necessary
        if image.mode not in ('L', 'RGB', 'RGBA'):
            image = image.convert('RGBA')
        
        for size in self.field.sizes:
            # Pre-create all of the thumbnail sizes.
            self.create_and_store_thumb(image, size)
            
        #blah = getattr(self, 'url_%d_%d' % (100, 100))
        #print "BLAH", blah
            
    def _calc_thumb_size_filename(self, size):
        """
        Calculates the correct filename for a would-be (or potentially
        existing) thumbnail of the given size.
        
        NOTE: This includes the path leading up to the thumbnail. IE:
        uploads/cbid_images/photo.png
        
        size: (tuple) In the format of (width, height)
        
        Returns a string filename.
        """
        filename_split = self.name.rsplit('.',1)
        file_name = filename_split[0]
        
        file_extension = self.get_thumbnail_format()
        
        (w, h) = size
        # somethumb_100x100.png, for example
        #print '%s_%sx%s.%s' % (file_name, w, h, file_extension)
        return '%s_%sx%s.%s' % (file_name, w, h, file_extension)
    
    def create_and_store_thumb(self, image, size):
        """
        Given that 'content' is a File object, create a thumbnail for the
        given size tuple and store it via the storage backend.
        """
        thumb_name = self._calc_thumb_size_filename(size)
        file_extension = self.get_thumbnail_format()
                
        # The work starts here.
        thumb_content = generate_thumb(image, size, file_extension)
        # Save the result to the storage backend.
        thumb_name_ = self.storage.save(thumb_name, thumb_content)        
        
        # Some back-ends don't like over-writing stuff. I guess. Not sure
        # if this is necessary.
        if not thumb_name == thumb_name_:
            raise ValueError('There is already a file named %s' % thumb_name)
        
    def delete(self, save=True):
        """
        Deletes the original, plus any thumbnails. Fails silently if there
        are errors deleting the thumbnails.
        """
        for size in self.field.sizes:
            thumb_name = self._calc_thumb_size_filename(size)
            self.storage.delete(thumb_name)

        super(ImageWithThumbsFieldFile, self).delete(save)
                        
class ImageWithThumbsField(ImageField):
    attr_class = ImageWithThumbsFieldFile
    """
    Usage example:
    ==============
    photo = ImageWithThumbsField(upload_to='images', sizes=((125,125),(300,200),)
    
    To retrieve image URL, exactly the same way as with ImageField:
        my_object.photo.url
    To retrieve thumbnails URL's just add the size to it:
        my_object.photo.url_125x125
        my_object.photo.url_300x200
    
    Note: The 'sizes' attribute is not required. If you don't provide it, 
    ImageWithThumbsField will act as a normal ImageField
        
    How it works:
    =============
    For each size in the 'sizes' atribute of the field it generates a 
    thumbnail with that size and stores it following this format:
    
    available_filename.[width]x[height].extension

    Where 'available_filename' is the available filename returned by the storage
    backend for saving the original file.
    
    Following the usage example above: For storing a file called "photo.jpg" it saves:
    photo.jpg          (original file)
    photo.125x125.jpg  (first thumbnail)
    photo.300x200.jpg  (second thumbnail)
    
    With the default storage backend if photo.jpg already exists it will use these filenames:
    photo_.jpg
    photo_.125x125.jpg
    photo_.300x200.jpg
    
    With the S3BotoStorage backends, the default is to over-write existing files.
    
    Note: django-thumbs assumes that if filename "any_filename.jpg" is available 
    filenames with this format "any_filename.[width]x[height].jpg" will be available, too.
    
    To do:
    ======
    Add method to regenerate thumbnails
    
    """
    def __init__(self, verbose_name=None, name=None, thumbnail_format=None,
                 width_field=None, height_field=None, sizes=(), **kwargs):
        self.verbose_name = verbose_name
        self.name = name
        self.width_field = width_field
        self.height_field = height_field
        self.sizes = sizes
        self.thumbnail_format = thumbnail_format
        super(ImageField, self).__init__(validators=[image_extension_validator], **kwargs)
        
    def south_field_triple(self):
        """
        Return a suitable description of this field for South.
        """
        from south.modelsinspector import introspector
        field_class = 'django.db.models.fields.files.ImageField'
        args, kwargs = introspector(ImageField)
        return (field_class, args, kwargs)
