"""
Much of this module was taken/inspired from sorl-thumbnails, by mikko and
smileychris. In simple cases, we retain compatibility with sorl-thumbnails, but
we don't generate thumbs on the fly (they are generated at the time of upload,
and only the specified sizes).

Sources from sorl-thumbnails in this module are Copyright (c) 2007, 
Mikko Hellsing, Chris Beaven.

Modifications and new ideas, Copyright (c) 2010, DUO Interactive, LLC.
"""
import re
import math
from django.template import Library, Node, Variable, VariableDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.utils.encoding import force_unicode

register = Library()

# Various regular expressions compiled here to avoid having to compile them
# repeatedly.
REGEXP_THUMB_SIZES = re.compile(r'(\d+)x(\d+)$')
REGEXP_ARGS = re.compile('(?<!quality)=')

# List of valid keys for key=value tag arguments.
TAG_SETTINGS = ['force_ssl']

def split_args(args):
    """
    Split a list of argument strings into a dictionary where each key is an
    argument name.

    An argument looks like ``force_ssl=True``.
    """
    if not args:
        return {}

    # Handle the old comma separated argument format.
    if len(args) == 1 and not REGEXP_ARGS.search(args[0]):
        args = args[0].split(',')

    # Separate out the key and value for each argument.
    args_dict = {}
    for arg in args:
        split_arg = arg.split('=', 1)
        value = len(split_arg) > 1 and split_arg[1] or None
        args_dict[split_arg[0]] = value

    return args_dict

class ThumbnailNode(Node):
    """
    Handles the rendering of a thumbnail URL, based on the input gathered
    from the thumbnail() tag function.
    """
    def __init__(self, source_var, size_var, opts=None,
                 context_name=None, **kwargs):
        # Name of the object/attribute pair, ie: some_obj.image
        self.source_var = source_var
        # Typically a string, '85x85'.
        self.size_var = size_var
        self.opts = opts
        # If an 'as some_var' is given, this is the context variable name
        # to store the URL in instead of returning it for rendering.
        self.context_name = context_name
        # Storage for optional keyword args processed by the tag parser.
        self.kwargs = kwargs

    def render(self, context):
        try:
            # This evaluates to a ImageWithThumbsField, as long as the
            # user specified a valid model field.
            relative_source = Variable(self.source_var).resolve(context)
        except VariableDoesNotExist:
            if settings.DEBUG:
                raise VariableDoesNotExist("Variable '%s' does not exist." %
                        self.source_var)
            else:
                relative_source = None

        try:
            requested_size = Variable(self.size_var).resolve(context)
        except VariableDoesNotExist:
            if settings.DEBUG:
                raise TemplateSyntaxError("Size argument '%s' is not a"
                        " valid size nor a valid variable." % self.size_var)
            else:
                requested_size = None

        # Size variable can be either a tuple/list of two integers or a valid
        # string, only the string is checked.
        else:
            if isinstance(requested_size, basestring):
                m = REGEXP_THUMB_SIZES.match(requested_size)
                if m:
                    requested_size = (int(m.group(1)), int(m.group(2)))
                elif settings.DEBUG:
                    raise TemplateSyntaxError("Variable '%s' was resolved but "
                            "'%s' is not a valid size." %
                            (self.size_var, requested_size))
                else:
                    requested_size = None

        if relative_source is None or requested_size is None:
            # Couldn't resolve the given template variable. Fail silently.
            thumbnail = ''
        else:
            # This is typically a athumb.fields.ImageWithThumbsFieldFile object.
            thumb_width, thumb_height = requested_size
            try:
                # Allow the user to override the protocol in the tag.
                force_ssl = self.kwargs.get('force_ssl', False)
                # Try to detect SSL mode in the request context. Front-facing
                # server or proxy must be passing the correct headers for
                # this to work. Also, factor in force_ssl.
                ssl_mode = self.is_secure(context) or force_ssl
                # Get the URL for the thumbnail from the
                # ImageWithThumbsFieldFile object.  
                thumbnail = relative_source.generate_url(thumb_width,
                                                         thumb_height,
                                                         ssl_mode=ssl_mode)
            except ValueError:
                # This file object doesn't actually have a file. Probably
                # model field with a None value.
                thumbnail = ''

        # Return the thumbnail class, or put it on the context
        if self.context_name is None:
            return thumbnail

        # We need to get here so we don't have old values in the context
        # variable.
        context[self.context_name] = thumbnail

        return ''
    
    def is_secure(self, context):
        """
        Looks at the RequestContext object and determines if this page is
        secured with SSL. Linking unencrypted media on an encrypted page will
        show a warning icon on some browsers. We need to be able to serve from
        an encrypted source for encrypted pages, if our backend supports it.

        'django.core.context_processors.request' must be added to
        TEMPLATE_CONTEXT_PROCESSORS in settings.py.
        """
        return 'request' in context and context['request'].is_secure()


def thumbnail(parser, token):
    """
    Creates a thumbnail of for an ImageField.

    To just output the absolute url to the thumbnail::

        {% thumbnail image 80x80 %}

    After the image path and dimensions, you can put any options::

        {% thumbnail image 80x80 force_ssl=True %}

    To put the thumbnail URL on the context instead of just rendering
    it, finish the tag with ``as [context_var_name]``::

        {% thumbnail image 80x80 as thumb %}
        <img src="{{thumb}}" />
    """
    args = token.split_contents()
    tag = args[0]
    # Check to see if we're setting to a context variable.
    if len(args) > 4 and args[-2] == 'as':
        context_name = args[-1]
        args = args[:-2]
    else:
        context_name = None

    if len(args) < 3:
        raise TemplateSyntaxError("Invalid syntax. Expected "
            "'{%% %s source size [option1 option2 ...] %%}' or "
            "'{%% %s source size [option1 option2 ...] as variable %%}'" %
            (tag, tag))

    # Get the source image path and requested size.

    source_var = args[1]
    # If the size argument was a correct static format, wrap it in quotes so
    # that it is compiled correctly.
    m = REGEXP_THUMB_SIZES.match(args[2])
    if m:
        args[2] = '"%s"' % args[2]
    size_var = args[2]

    # Get the options.
    args_list = split_args(args[3:]).items()

    # Check the options.
    opts = {}
    kwargs = {} # key,values here override settings and defaults

    for arg, value in args_list:
        value = value and parser.compile_filter(value)
        if arg in TAG_SETTINGS and value is not None:
            kwargs[str(arg)] = value
            continue
        if arg in VALID_OPTIONS:
            opts[arg] = value
        else:
            raise TemplateSyntaxError("'%s' tag received a bad argument: "
                                      "'%s'" % (tag, arg))
    return ThumbnailNode(source_var, size_var, opts=opts,
                         context_name=context_name, **kwargs)

register.tag(thumbnail)
