import os
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    args = '<app.model> <field>'
    help = 'Re-generates thumbnails for all instances of the given model, for the given field.'

    def handle(self, *args, **options):
        self.args = args
        self.options = options

        self.validate_input()
        self.parse_input()
        self.regenerate_thumbs()

    def validate_input(self):
        num_args = len(self.args)

        if num_args < 2:
            raise CommandError("Please pass the app.model and the field to generate thumbnails for.")
        if num_args > 2:
            raise CommandError("Too many arguments provided.")

        if '.' not in self.args[0]:
            raise CommandError("The first argument must be in the format of: app.model")

    def parse_input(self):
        """
        Go through the user input, get/validate some important values.
        """
        app_split = self.args[0].split('.')
        app = app_split[0]
        model_name = app_split[1].lower()

        try:
            self.model = ContentType.objects.get(app_label=app, model=model_name)
            self.model = self.model.model_class()
        except ContentType.DoesNotExist:
            raise CommandError("There is no app/model combination: %s" % self.args[0])

        # String field name to re-generate.
        self.field = self.args[1]

    def regenerate_thumbs(self):
        """
        Handle re-generating the thumbnails. All this involves is reading the
        original file, then saving the same exact thing. Kind of annoying, but
        it's simple.
        """
        Model = self.model
        instances = Model.objects.all()
        num_instances = instances.count()

        counter = 1
        for instance in instances:
            file = getattr(instance, self.field)
            if not file:
                print "(Skipped)"
                counter += 1
                continue

            file_name = os.path.basename(file.name)
            # Keep them informed on the progress.
            print "(%d/%d) %s" % (counter, num_instances, file_name)

            try:
                fdat = file.read()
            except IOError:
                # Key didn't exist.
                print "(Skipped)"
                counter += 1
                continue

            try:
                file_contents = ContentFile(fdat)
            except ValueError:
                # This field has no file associated with it, skip it.
                print "(Skipped)"
                counter += 1
                continue

            # Saving pumps it back through the thumbnailer, if this is a
            # ThumbnailField. If not, it's still pretty harmless.
            file.save(file_name, file_contents)
            counter += 1
