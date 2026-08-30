"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*', '.localhost', '127.0.0.1']

# MinIO (local S3-compatible storage for development/testing)
AWS_ACCESS_KEY_ID = 'minioadmin'
AWS_SECRET_ACCESS_KEY = 'minioadmin'
AWS_STORAGE_BUCKET_NAME = 'sgca-evidencias'
AWS_S3_ENDPOINT_URL = 'http://minio:9000'
AWS_S3_REGION_NAME = 'us-east-1'
