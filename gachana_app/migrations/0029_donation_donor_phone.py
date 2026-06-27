from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0028_donation_guest_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='donor_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
