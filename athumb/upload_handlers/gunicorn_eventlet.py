"""
Upload handlers with small tweaks to work with gunicorn + eventlet async
workers. These should eventually become unnecessary as the supporting libraries
continue to improve.
"""
from django.core.files.uploadhandler import TemporaryFileUploadHandler
import eventlet

class EventletTmpFileUploadHandler(TemporaryFileUploadHandler):
    """
    Uploading large files can cause a worker thread to hang long enough to
    hit the timeout before the upload can be completed. Sleep long enough
    to hand things back to the other threads to avoid a timeout.
    """
    def receive_data_chunk(self, raw_data, start):
        """
        Over-ridden method to circumvent the worker timeouts on large uploads.
        """
        self.file.write(raw_data)
        # CHANGED: This un-hangs us long enough to keep things rolling.
        eventlet.sleep(0)