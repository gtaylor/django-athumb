#coding=utf-8
"""
Various functions for parsing user (developer) input. For example, parsing
a cropping a string value of '50% 50%' into cropping offsets.
"""
import re
from athumb.pial.helpers import ThumbnailError

class ThumbnailParseError(ThumbnailError):
    pass

_CROP_PERCENT_PATTERN = re.compile(r'^(?P<value>\d+)(?P<unit>%|px)$')

# The following two alias dicts put percentage values on some common
# X, Y cropping names. For example, center cropping is 50%.
_X_ALIAS_PERCENT = {
    'left': '0%',
    'center': '50%',
    'right': '100%',
}
_Y_ALIAS_PERCENT = {
    'top': '0%',
    'center': '50%',
    'bottom': '100%',
}

def get_cropping_offset(crop, epsilon):
    """
    Calculates the cropping offset for the cropped image. This only calculates
    the offset for one dimension (X or Y). This should be called twice to get
    the offsets for the X and Y dimensions.

    :param str crop: A percentage cropping value for the plane. This is in the
        form of something like '50%'.
    :param float epsilon: The difference between the original image's dimension
        (X or Y) and the desired crop window.
    :rtype: int
    :returns: The cropping offset for the given dimension.
    """
    m = _CROP_PERCENT_PATTERN.match(crop)
    if not m:
        raise ThumbnailParseError('Unrecognized crop option: %s' % crop)
    value = int(m.group('value')) # we only take ints in the regexp
    unit = m.group('unit')
    if unit == '%':
        value = epsilon * value / 100.0
        # return ∈ [0, epsilon]
    return int(max(0, min(value, epsilon)))

def parse_crop(crop, xy_image, xy_window):
    """
    Returns x, y offsets for cropping. The window area should fit inside
    image but it works out anyway

    :param str crop: A cropping offset string. This is either one or two
        space-separated values. If only one value is specified, the cropping
        amount (pixels or percentage) for both X and Y dimensions is the
        amount given. If two values are specified, X and Y dimension cropping
        may be set independently. Some examples: '50% 50%', '50px 20px',
        '50%', '50px'.
    :param tuple xy_image: The (x,y) dimensions of the image.
    :param tuple xy_window: The desired dimensions (x,y) of the cropped image.
    :raises: ThumbnailParseError in the event of invalid input.
    :rtype: tuple of ints
    :returns: A tuple of of offsets for cropping, in (x,y) format.
    """
    # Cropping percentages are space-separated by axis. For example:
    # '50% 75%' would be a 50% cropping ratio for X, and 75% for Y.
    xy_crop = crop.split(' ')
    if len(xy_crop) == 1:
        # Only one dimension was specified, use the same for both planes.
        if crop in _X_ALIAS_PERCENT:
            x_crop = _X_ALIAS_PERCENT[crop]
            y_crop = '50%'
        elif crop in _Y_ALIAS_PERCENT:
            y_crop = _Y_ALIAS_PERCENT[crop]
            x_crop = '50%'
        else:
            x_crop, y_crop = crop, crop
    elif len(xy_crop) == 2:
        # Separate X and Y cropping percentages specified.
        x_crop, y_crop = xy_crop
        x_crop = _X_ALIAS_PERCENT.get(x_crop, x_crop)
        y_crop = _Y_ALIAS_PERCENT.get(y_crop, y_crop)
    else:
        raise ThumbnailParseError('Unrecognized crop option: %s' % crop)

    # We now have cropping percentages for the X and Y planes.
    # Calculate the cropping offsets (in pixels) for each plane.
    offset_x = get_cropping_offset(x_crop, xy_image[0] - xy_window[0])
    offset_y = get_cropping_offset(y_crop, xy_image[1] - xy_window[1])
    return offset_x, offset_y
