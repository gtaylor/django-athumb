# -*- encoding: utf-8 -*-
"""
Thumbnailing and re-sizing algorithms
"""
import cStringIO
import math

from PIL import Image, ImageFilter, ImageChops
from django.core.files.base import ContentFile

def image_entropy(im):
    """
    Calculate the entropy of an image. Used for "smart cropping".
    
    Args:
        im: (PIL.Image) The image to calculate entropy for.
    """
    hist = im.histogram()
    hist_size = float(sum(hist))
    hist = [h / hist_size for h in hist]
    return - sum([p * math.log(p, 2) for p in hist if p != 0])

def sorl_scale_and_crop(im, thumb_options, format):
    """
    Generates a thumbnail image and returns a ContentFile object with the thumbnail
    
    Args:
        im: (PIL.Image) The original sized image.
        requested_size: (tuple) Desired thumbnail size, ie: (200,120)
        format: (str) format of the original image ('jpeg','gif','png',...)
            (this format will be used for the generated thumbnail, too)
        opts: (dict) Options defined in the model field.
            
    Returns:
        A Django ContentFile that may be saved to a field.
    """
    # Default this to smart cropping.
    crop = thumb_options.get('crop', 'smart')

    # Image's current size.
    x, y = [float(v) for v in im.size]
    # Desired size.
    xr, yr = [float(v) for v in thumb_options.get('size')]

    if crop:
        r = max(xr / x, yr / y)
    else:
        r = min(xr / x, yr / y)

    if r < 1.0 or (r > 1.0 and thumb_options.get('upscale', False)):
        im = im.resize((int(round(x * r)), int(round(y * r))), resample=Image.ANTIALIAS)

    if crop:
        # Difference (for x and y) between new image size and requested size.
        x, y = [float(v) for v in im.size]
        dx = x - min(x, xr)
        dy = y - min(y, yr)
        if dx or dy:
            if xr == yr:
                # quad
                xsize, ysize = im.size
                # get minimum size
                minsize = min(xsize, ysize)
                # largest square possible in the image
                xnewsize = (xsize - minsize) / 2
                ynewsize = (ysize - minsize) / 2
                # crop it
                im = im.crop((xnewsize, ynewsize, xsize - xnewsize, ysize - ynewsize))
                # load is necessary after crop                
                im.load()
                # thumbnail of the cropped image (with ANTIALIAS to make it look better)
                im.thumbnail((int(xr), int(yr)), Image.ANTIALIAS)
            # See if the image should be "smart cropped".
            else:
                # Center cropping (default).
                ex = int(dx / 2)
                ey = int(dy / 2)
                x = int(x)
                y = int(y)
                dx = int(dx)
                dy = int(dy)
                box = [ex, ey, x - ex, y - ey]
                left = top = 0
                right, bottom = x, y

                while dx:
                    slice = min(dx, 10)
                    l_sl = im.crop((0, 0, slice, y))
                    r_sl = im.crop((x - slice, 0, x, y))
                    if image_entropy(l_sl) >= image_entropy(r_sl):
                        right -= slice
                    else:
                        left += slice
                    dx -= slice
                while dy:
                    slice = min(dy, 10)
                    t_sl = im.crop((0, 0, x, slice))
                    b_sl = im.crop((0, y - slice, x, y))
                    if image_entropy(t_sl) >= image_entropy(b_sl):
                        bottom -= slice
                    else:
                        top += slice
                    dy -= slice
                box = (left, top, right, bottom)
                # Finally, crop the image!
                im = im.crop([int(round(v)) for v in box])

    io = cStringIO.StringIO()
    # PNG and GIF are the same, JPG is JPEG
    if format.upper() == 'JPG':
        format = 'JPEG'

    im.save(io, format)
    return ContentFile(io.getvalue())
