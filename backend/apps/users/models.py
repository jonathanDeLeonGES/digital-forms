from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, nombre_completo, role, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, nombre_completo=nombre_completo, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre_completo, role='admin', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, nombre_completo, role, password, **extra_fields)


class CustomUser(AbstractBaseUser):
    ROLES = [
        ('admin', 'Admin'),
        ('responsable', 'Responsable'),
        ('supervisor', 'Supervisor'),
        ('verificador', 'Verificador'),
    ]

    email = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_completo', 'role']

    objects = CustomUserManager()

    class Meta:
        app_label = 'users'

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser
