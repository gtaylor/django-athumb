from cStringIO import StringIO
from athumb.pial.engines.base import EngineBase

try:
    from PIL import Image, ImageFile, ImageDraw
except ImportError:
    import Image, ImageFile, ImageDraw

class PILEngine(EngineBase):
    """
    Python Imaging Library Engine. This implements members of EngineBase.
    """
    def get_image(self, source):
        """
        Given a file-like object, loads it up into a PIL.Image object
        and returns it.

        :param file source: A file-like object to load the image from.
        :rtype: PIL.Image
        :returns: The loaded image.
        """
        buf = StringIO(source.read())
        return Image.open(buf)

    def get_image_size(self, image):
        """
        Returns the image width and height as a tuple.

        :param PIL.Image image: An image whose dimensions to get.
        :rtype: tuple
        :returns: Dimensions in the form of (x,y).
        """
        return image.size

    def is_valid_image(self, raw_data):
        """
        Checks if the supplied raw data is valid image data.

        :param str raw_data: A string representation of the image data.
        :rtype: bool
        :returns: ``True`` if ``raw_data`` is valid, ``False`` if not.
        """
        buf = StringIO(raw_data)
        try:
            trial_image = Image.open(buf)
            trial_image.verify()
        except Exception:
            # TODO: Get more specific with this exception handling.
            return False
        return True

    def _colorspace(self, image, colorspace):
        """
        Sets the image's colorspace. This is typical 'RGB' or 'GRAY', but
        may be other things, depending on your choice of Engine.

        :param PIL.Image image: The image whose colorspace to adjust.
        :param str colorspace: One of either 'RGB' or 'GRAY'.
        :rtype: PIL.Image
        :returns: The colorspace-adjusted image.
        """
        if colorspace == 'RGB':
            if image.mode == 'RGBA':
                # RGBA is just RGB + Alpha
                return image
            if image.mode == 'P' and 'transparency' in image.info:
                return image.convert('RGBA')
            return image.convert('RGB')
        if colorspace == 'GRAY':
            return image.convert('L')
        return image

    def _scale(self, image, width, height):
        """
        Given an image, scales the image to the given ``width`` and ``height``.

        :param PIL.Image image: The image to scale.
        :param int width: The width of the scaled image.
        :param int height: The height of the scaled image.
        :rtype: PIL.Image
        :returns: The scaled image. 
        """
        return image.resize((width, height), resample=Image.ANTIALIAS)

    def _crop(self, image, width, height, x_offset, y_offset):
        """
        Crops the ``image``, starting at ``width`` and ``height``, adding the
        ``x_offset`` and ``y_offset`` to make the crop window.

        :param PIL.Image image: The image to crop.
        :param int width: The X plane's start of the crop window.
        :param int height: The Y plane's start of the crop window.
        :param int x_offset: The 'width' of the crop window.
        :param int y_offset: The 'height' of the crop window.
        :rtype: PIL.Image
        :returns: The cropped image.
        """
        return image.crop((x_offset, y_offset,
                           width + x_offset, height + y_offset))

    def _get_raw_data(self, image, format, quality):
        """
        Returns the raw data from the Image, which can be directly written
        to a something, be it a file-like object or a database.

        :param PIL.Image image: The image to get the raw data for.
        :param str format: The format to save to. If this value is ``None``,
            PIL will attempt to guess. You're almost always better off
            providing this yourself. For a full list of formats, see the PIL
            handbook at:
            http://www.pythonware.com/library/pil/handbook/index.htm
            The *Appendixes* section at the bottom, in particular.
        :param int quality: A quality level as a percent. The lower, the
            higher the compression, the worse the artifacts. Check the
            format's handbook page for what the different values for this mean.
            For example, JPEG's max quality level is 95, with 100 completely
            disabling JPEG quantization.
        :rtype: str
        :returns: A string representation of the image.
        """
        ImageFile.MAXBLOCK = 1024 * 1024
        buf = StringIO()

        try:
            # ptimize makes the encoder do a second pass over the image, if
            # the format supports it.
            image.save(buf, format=format, quality=quality, optimize=1)
        except IOError:
            # optimize is a no-go, omit it this attempt.
            image.save(buf, format=format, quality=quality)

        raw_data = buf.getvalue()
        buf.close()
        return raw_data

