from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_userprofile_notification_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='user_urgency',
            field=models.CharField(
                choices=[
                    ('low', 'Низкая'),
                    ('normal', 'Обычная'),
                    ('urgent', 'Срочно'),
                    ('critical', 'Критично'),
                ],
                default='normal',
                max_length=20,
                verbose_name='Запрошенная срочность',
            ),
        ),
    ]
