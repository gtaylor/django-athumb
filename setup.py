from distutils.core import setup
import athumb

long_description = open('README.rst').read()

setup(
    name='django-athumb',
    version=athumb.VERSION,
    packages=['athumb', 'athumb.backends', 'athumb.management',
              'athumb.pial', 'athumb.pial.engines',
              'athumb.management.commands', 'athumb.templatetags',
              'athumb.upload_handlers'],
    description='A simple, S3-backed thumbnailer field.',
    long_description=long_description,
    author='Gregory Taylor',
    author_email='gtaylor@gc-taylor.com',
    license='BSD License',
    url='http://github.com/gtaylor/django-athumb',
    platforms=["any"],
    requires=['django', 'boto', 'pil'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Environment :: Web Environment',
    ],
)
