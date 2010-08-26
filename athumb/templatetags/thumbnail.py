import re
import math
from django.template import Library, Node, Variable, VariableDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.utils.encoding import force_unicode

register = Library()

size_pat = re.compile(r'(\d+)x(\d+)$')

def split_args(args):
    """
    Split a list of argument strings into a dictionary where each key is an
    argument name.

    An argument looks like ``crop``, ``crop="some option"`` or ``crop=my_var``.
    Arguments which provide no value get a value of ``None``.
    """
    if not args:
        return {}
    # Handle the old comma separated argument format.
    if len(args) == 1 and not re_new_args.search(args[0]):
        args = args[0].split(',')
    # Separate out the key and value for each argument.
    args_dict = {}
    for arg in args:
        split_arg = arg.split('=', 1)
        value = len(split_arg) > 1 and split_arg[1] or None
        args_dict[split_arg[0]] = value
    return args_dict

class ThumbnailNode(Node):
    def __init__(self, source_var, size_var, opts=None,
                 context_name=None, **kwargs):
        self.source_var = source_var
        self.size_var = size_var
        self.opts = opts
        self.context_name = context_name
        self.kwargs = kwargs

    def render(self, context):
        DEBUG = settings.DEBUG
        try:
            # A file object will be allowed in DjangoThumbnail class
            relative_source = Variable(self.source_var).resolve(context)
        except VariableDoesNotExist:
            if DEBUG:
                raise VariableDoesNotExist("Variable '%s' does not exist." %
                        self.source_var)
            else:
                relative_source = None
        try:
            requested_size = Variable(self.size_var).resolve(context)
        except VariableDoesNotExist:
            if DEBUG:
                raise TemplateSyntaxError("Size argument '%s' is not a"
                        " valid size nor a valid variable." % self.size_var)
            else:
                requested_size = None
        # Size variable can be either a tuple/list of two integers or a valid
        # string, only the string is checked.
        else:
            if isinstance(requested_size, basestring):
                m = size_pat.match(requested_size)
                if m:
                    requested_size = (int(m.group(1)), int(m.group(2)))
                elif DEBUG:
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
                thumbnail = relative_source.generate_url(thumb_width,
                                                         thumb_height)
            except ValueError:
                # This file object doesn't actually have a file. Probably
                # model field with a None value.
                thumbnail = None

        # Return the thumbnail class, or put it on the context
        if self.context_name is None:
            return thumbnail

        # We need to get here so we don't have old values in the context
        # variable.
        context[self.context_name] = thumbnail

        return ''


def thumbnail(parser, token):
    """
    Creates a thumbnail of for an ImageField.

    To just output the absolute url to the thumbnail::

        {% thumbnail image 80x80 %}

    After the image path and dimensions, you can put any options::

        {% thumbnail image 80x80 quality=95 crop %}

    To put the DjangoThumbnail class on the context instead of just rendering
    the absolute url, finish the tag with ``as [context_var_name]``::

        {% thumbnail image 80x80 as thumb %}
        {{ thumb.width }} x {{ thumb.height }}
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
    m = size_pat.match(args[2])
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
