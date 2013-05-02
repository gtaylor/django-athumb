from storages.backends import s3boto


class S3BotoStorage(s3boto.S3BotoStorage):
    """
    This is largely here to maintain backwards compatibility with legacy
    installs, since we at one time had a custom fork of django-storages
    in here. Eventually we'll try to get rid of this.
    """

    def url_as_attachment(self, name, filename=None):
        """
        This goes outside of Django's storage API, but we found it handy for
        our purposes. It generates a URL that will cause S3 to reply with
        a content-disposition header, allowing the file to be downloaded as
        an attachment.

        :param basestring name: The name of the key in S3.
        :keyword basestring filename: If specified, allows you to rename the
            attachment, instead of using the default (the key name).
        """

        name = self._clean_name(name)

        if filename:
            disposition = 'attachment; filename="%s"' % filename
        else:
            disposition = 'attachment;'

        response_headers = {
            'response-content-disposition': disposition,
        }

        return self.connection.generate_url(
            self.querystring_expire, 'GET',
            bucket=self.bucket.name, key=name,
            query_auth=True,
            force_http=not self.secure_urls,
            response_headers=response_headers)


class S3BotoStorage_AllPublic(S3BotoStorage):
    """
    Same as S3BotoStorage, but defaults to uploading everything with a
    public acl. This has two primary benefits:

    1) Non-encrypted requests just make a lot better sense for certain things
       like profile images. Much faster, no need to generate S3 auth keys.
    2) Since we don't have to hit S3 for auth keys, this backend is much
       faster than S3BotoStorage, as it makes no attempt to validate whether
       keys exist.
    """

    def __init__(self, **kwargs):
        super(S3BotoStorage_AllPublic, self).__init__(
            acl='public-read',
            querystring_auth=False,
            secure_urls=False,
            **kwargs
        )