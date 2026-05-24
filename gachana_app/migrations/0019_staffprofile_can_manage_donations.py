from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0018_donation_banks'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffprofile',
            name='can_manage_donations',
            field=models.BooleanField(
                default=False,
                help_text='When enabled, this staff member can review and confirm donations in the portal.',
            ),
        ),
    ]
