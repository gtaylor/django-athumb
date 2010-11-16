import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    args = '<app.model> <field>'
    help = 'Enrolls an existing user to an ClassSection.'

    def validate_input(self):
        num_args = len(self.args)
        
        if num_args < 2:
            raise CommandError("Please pass the app.model and the field to generate thumbnails for.")
        if num_args > 2:
            raise CommandError("Too many arguments provided.")
        
        if '.' not in self.args[0]:
            raise CommandError("The first argument must be in the format of: app.model")

    def parse_input(self):
        app_split = self.args[0].split('.')
        app = app_split[0]
        model_name = app_split[1].lower()
        
        try:
            self.model = ContentType.objects.get(app_label=app, model=model_name)
            self.model = self.model.model_class()
        except ContentType.DoesNotExist:
            raise CommandError("There is no app/model combination: %s" % self.args[0])
        
        self.field = self.args[1]
        
    def handle(self, *args, **options):
        self.args = args
        self.options = options
        
        self.validate_input()
        self.parse_input()
        
        Model = self.model
        instances = Model.objects.all()
        
        for instance in instances:
            file = getattr(instance, self.field)
            if not file:
                continue

            field = file.field

            name = os.path.basename(file.name)
            content = instance.image

            #print "SCHOOL", instance, instance.id
            #print "FILE", file, type(file)
            #print "NAME", name, type(name)
            #print "CONTENT", content, type(content)
            instance.image.save(name, content)