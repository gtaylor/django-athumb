# django-athumb

Storing images and their thumbnails on S3 is a bit of a clumbsy endeavor with
Django. While this Django app may work with more typical storage backends, it
is intended to accept image uploads, thumbnail them, and upload the original
plus the thumbs to S3. You may then get to the thumbnails in your template
by doing something like:

    <img src="{% thumbnail some_obj.image 80x80 %}" />
    
This automatically assembles the remote S3 URL to retrieve the thumbnail from.
No error checking is done, and several assumptions are made for the sake of
speed.

* If you need a very basic thumbnailer, this is probably what you're looking for.
* If your needs are more complicated than just re-sizing images and uploading
  them to S3, this is probably not what you're looking for (unless you'd like to
  hack on it a bit).

All code is under a BSD-style license, see LICENSE for details.

Source: http://github.com/duointeractive/django-athumb

## Requirements

- python >= 2.5

- django >= 1.0

- boto >= 1.8d <= 2.0

## Installation

To install run

    python setup.py install

which will install the application into python's site-packages directory. 

## Configuration

### settings.py

Add to INSTALLED_APPS:

	'athumb'

Add to TEMPLATE_CONTEXT_PROCESSORS in settings.py:

    'django.core.context_processors.request'

If you want S3 storage as your default file back-end:

    # If you don't want this to be the global default, just make sure you
    # specify the S3BotoStorage_AllPublic backend on a per-field basis.
    DEFAULT_FILE_STORAGE = 'athumb.backends.s3boto.S3BotoStorage_AllPublic'
    
Then setup some values used by the backend:
    
    AWS_ACCESS_KEY_ID = 'YourS3AccessKeyHere'
    AWS_SECRET_ACCESS_KEY = 'YourS3SecretAccessKeyHere'
    AWS_STORAGE_BUCKET_NAME = 'OneOfYourBuckets'

### Backends

django-athumb comes with a simplified s3boto backend, modified from those found
in the django-storages project. For most cases, you'll want to use
athumb.backends.s3boto.S3BotoStorage_AllPublic, as it does not use HTTPS, and
is a good bit faster than S3BotoStorage because it makes some assumptions.

NOTE: This package is primarily aimed at serving S3 thumbnails, I have not
tested it at all with the Django standard backend.

## Template Tags

When referring to media in HTML templates you can use custom template tags. 
These tags can by accessed by loading the athumb template tag collection.

	{% load thumbnail %}

If you'd like to make the athumb tags global, you can add the following to
your master urls.py file:

    from django.template import add_to_builtins
    add_to_builtins('athumb.templatetags.thumbnail')

Some backends (S3) support https URLs when the requesting page is secure.
In order for the https to be detected, the request must be placed in the
template context with the key 'request'. This can be done automatically by adding
'django.core.context_processors.request' to __TEMPLATE\_CONTEXT\_PROCESSORS__
in settings.py

#### thumbnail

Creates a thumbnail of for an ImageField.

To just output the absolute url to the thumbnail:

    {% thumbnail some_obj.image 80x80 %}

As long as you've got Django's request context processor in, the thumbnail tag
will detect when the current view is being served over SSL, and automatically
convert any http to https in the thumbnail URL. If you want to always force
SSL for a thumbnail, add it as an argument like this:

    {% thumbnail some_obj.image 80x80 force_ssl=True %}

To put the thumbnail URL on the context instead of just rendering
it, finish the tag with `as [context_var_name]`:

    {% thumbnail image 80x80 as thumb %}
    <img src="{{thumb}}" />

## To-Do

* See the issue tracker for a list of outstanding things needing doing.

## Change Log

### 1.0

* Initial release.