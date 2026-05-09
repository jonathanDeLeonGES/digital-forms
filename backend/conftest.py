import os

# Valores por defecto para correr pytest directamente en el host
# (con el puerto 5432 de PostgreSQL mapeado desde Docker).
# Cuando pytest corre DENTRO del contenedor, docker-compose ya
# inyecta estas variables desde .env.dev y los setdefault no tienen efecto.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DB_NAME", "sgca")
os.environ.setdefault("DB_USER", "sgca")
os.environ.setdefault("DB_PASSWORD", "sgca_dev_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
