from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0007_userprofile_notify_email_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="office_room",
            field=models.CharField(blank=True, max_length=50, verbose_name="Кабинет"),
        ),
    ]
