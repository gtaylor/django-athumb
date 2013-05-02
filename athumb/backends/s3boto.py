from storages.backends.s3boto import S3BotoStorage


class S3BotoStorage_AllPublic(S3BotoStorage):
    """
    Same as S3BotoStorage, but defaults to uploading everything with a
    public acl. This has two primary beenfits:

    1) Non-encrypted requests just make a lot better sense for certain things
       like profile images. Much faster, no need to generate S3 auth keys.
    2) Since we don't have to hit S3 for auth keys, this backend is much
       faster than S3BotoStorage, as it makes no attempt to validate whether
       keys exist.

    WARNING: This backend makes absolutely no attempt to verify whether the
    given key exists on self.url(). This is much faster, but be aware.
    """
    def __init__(self, *args, **kwargs):
        super(S3BotoStorage_AllPublic, self).__init__(
            acl='public-read',
            querystring_auth=False,
            secure_urls=False,
            *args,
            **kwargs
        )

    def url(self, name):
        """
        Since we assume all public storage with no authorization keys, we can
        just simply dump out a URL rather than having to query S3 for new keys.
        """
        name = super(S3BotoStorage_AllPublic, self)._normalize_name(super(S3BotoStorage_AllPublic, self)._clean_name(name))

        if self.custom_domain:
            return "%s//%s/%s" % (self.url_protocol, self.custom_domain, name)
        if self.bucket_name:
            return "%s//%s/%s" % (self.url_protocol, self.bucket_name, name)
        # No bucket ? Then it's the default region
        return "http://s3.amazonaws.com/%s/%s" % (self.bucket, name)
