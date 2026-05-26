from storages.backends.s3boto3 import S3Boto3Storage


class TenantMediaStorage(S3Boto3Storage):
    """S3/MinIO storage with per-tenant path namespacing.

    All files are stored under {tenant_slug}/evidencias/... so objects from
    different tenants never collide even when sharing a single bucket.
    """

    def __init__(self, tenant_slug: str, **kwargs):
        super().__init__(**kwargs)
        self._tenant_slug = tenant_slug

    def _normalize_name(self, name: str) -> str:
        normalized = super()._normalize_name(name)
        if not normalized.startswith(self._tenant_slug + '/'):
            normalized = f"{self._tenant_slug}/{normalized}"
        return normalized
