from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0006_ticket_user_urgency"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="notify_email_address",
            field=models.EmailField(blank=True, max_length=254, verbose_name="Email для уведомлений"),
        ),
    ]
