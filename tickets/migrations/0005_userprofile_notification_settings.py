from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_workstation_ticket_workstation'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='notify_browser',
            field=models.BooleanField(default=True, verbose_name='Уведомления в браузере'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_email',
            field=models.BooleanField(default=True, verbose_name='Email уведомления'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_vk',
            field=models.BooleanField(default=False, verbose_name='VK уведомления'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='vk_user_id',
            field=models.CharField(blank=True, max_length=100, verbose_name='VK ID'),
        ),
    ]
