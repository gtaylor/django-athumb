from django.template import Library
from thumbnail import thumbnail

register = Library()

register.tag(thumbnail)
