from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_userprofile_office_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='workstation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='tickets.workstation',
                verbose_name='Рабочее место/Компьютер',
            ),
        ),
    ]
