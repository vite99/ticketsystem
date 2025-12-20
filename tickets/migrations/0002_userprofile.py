# Generated migration for UserProfile model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_approved', models.BooleanField(default=False, verbose_name='Одобрен администратором')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата одобрения')),
                ('department', models.CharField(blank=True, max_length=100, verbose_name='Отдел')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='Телефон')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_users', to=settings.AUTH_USER_MODEL, verbose_name='Одобрен пользователем')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Профиль пользователя',
                'verbose_name_plural': 'Профили пользователей',
            },
        ),
    ]
