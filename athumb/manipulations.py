# -*- encoding: utf-8 -*-
"""
Thumbnailing and re-sizing algorithms
"""
import cStringIO
import re

from PIL import Image, ImageFilter, ImageChops
from django.core.files.base import ContentFile

def generate_thumb_basic(orig_image, thumb_size, format):
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
        minsize = min(xsize, ysize)
        # largest square possible in the image
        xnewsize = (xsize - minsize) / 2
        ynewsize = (ysize - minsize) / 2
        # crop it
        image2 = image.crop((xnewsize, ynewsize, xsize - xnewsize, ysize - ynewsize))
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
    # Image's current size.
    x, y = [float(v) for v in im.size]
    # Desired size.
    xr, yr = [float(v) for v in thumb_options.get('size')]

    if thumb_options.get('crop', False):
        r = max(xr / x, yr / y)
    else:
        r = min(xr / x, yr / y)

    if r < 1.0 or (r > 1.0 and thumb_options.get('upscale', False)):
        im = im.resize((int(round(x * r)), int(round(y * r))), resample=Image.ANTIALIAS)

    crop = thumb_options.get('crop', False) or thumb_options.has_key('crop')
    if crop:
        # Difference (for x and y) between new image size and requested size.
        x, y = [float(v) for v in im.size]
        dx, dy = (x - min(x, xr)), (y - min(y, yr))
        if dx or dy:
            # Center cropping (default).
            ex, ey = dx / 2, dy / 2
            box = [ex, ey, x - ex, y - ey]
            # See if an edge cropping argument was provided.
            edge_crop = (isinstance(crop, basestring) and
                           re.match(r'(?:(-?)(\d+))?,(?:(-?)(\d+))?$', crop))
            if edge_crop and filter(None, edge_crop.groups()):
                x_right, x_crop, y_bottom, y_crop = edge_crop.groups()
                if x_crop:
                    offset = min(x * int(x_crop) / 100, dx)
                    if x_right:
                        box[0] = dx - offset
                        box[2] = x - offset
                    else:
                        box[0] = offset
                        box[2] = x - (dx - offset)
                if y_crop:
                    offset = min(y * int(y_crop) / 100, dy)
                    if y_bottom:
                        box[1] = dy - offset
                        box[3] = y - offset
                    else:
                        box[1] = offset
                        box[3] = y - (dy - offset)
            # See if the image should be "smart cropped".
            elif crop == 'smart':
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
