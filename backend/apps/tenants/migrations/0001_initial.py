import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # 1. Plan — no FKs
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(
                    choices=[('trial', 'Trial'), ('enterprise', 'Enterprise')],
                    max_length=20,
                    unique=True,
                )),
            ],
            options={'app_label': 'tenants'},
        ),
        # 2. Tenant — TenantMixin provides schema_name; our fields are nombre_empresa, email_admin, created_at
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('schema_name', models.CharField(
                    db_index=True,
                    max_length=63,
                    unique=True,
                    verbose_name='Schema name',
                )),
                ('nombre_empresa', models.CharField(max_length=200)),
                ('email_admin', models.EmailField(max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'app_label': 'tenants'},
        ),
        # 3. Domain — DomainMixin; FK to Tenant
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(db_index=True, max_length=253, unique=True, verbose_name='Domain URL')),
                ('is_primary', models.BooleanField(db_index=True, default=True, verbose_name='Primary')),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='domains',
                    to='tenants.tenant',
                    verbose_name='Tenant',
                )),
            ],
            options={'app_label': 'tenants'},
        ),
        # 4. Subscription — OneToOne Tenant, FK Plan
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(auto_now_add=True)),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('num_licencias', models.PositiveIntegerField(blank=True, null=True)),
                ('tenant', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscription',
                    to='tenants.tenant',
                )),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='tenants.plan',
                )),
            ],
            options={'app_label': 'tenants'},
        ),
    ]
