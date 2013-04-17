import os
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.db.models.loading import get_model

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
        
        self.model = get_model(app, model_name)

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
        # Filenames are keys in here, to help avoid re-genning something that
        # we have already done.
        regen_tracker = {}

        counter = 1
        for instance in instances:
            file = getattr(instance, self.field)
            if not file:
                print "(%d/%d) ID: %d -- Skipped -- No file" % (counter,
                                                                num_instances,
                                                                instance.id)
                counter += 1
                continue

            file_name = os.path.basename(file.name)

            if regen_tracker.has_key(file_name):
                print "(%d/%d) ID: %d -- Skipped -- Already re-genned %s" % (
                                                    counter,
                                                    num_instances,
                                                    instance.id,
                                                    file_name)
                counter += 1
                continue

            # Keep them informed on the progress.
            print "(%d/%d) ID: %d -- %s" % (counter, num_instances,
                                            instance.id, file_name)

            try:
                fdat = file.read()
                file.close()
                del file.file
            except IOError:
                # Key didn't exist.
                print "(%d/%d) ID %d -- Error -- File missing on S3" % (
                                                              counter,
                                                              num_instances,
                                                              instance.id)
                counter += 1
                continue

            try:
                file_contents = ContentFile(fdat)
            except ValueError:
                # This field has no file associated with it, skip it.
                print "(%d/%d) ID %d --  Skipped -- No file on field)" % (
                                                              counter,
                                                              num_instances,
                                                              instance.id)
                counter += 1
                continue

            # Saving pumps it back through the thumbnailer, if this is a
            # ThumbnailField. If not, it's still pretty harmless.

            try:
                file.generate_thumbs(file_name, file_contents)
            except IOError, e:
                print "(%d/%d) ID %d --  Error -- Image may be corrupt)" % (
                    counter,
                    num_instances,
                    instance.id)
                counter += 1
                continue

            regen_tracker[file_name] = True
            counter += 1
