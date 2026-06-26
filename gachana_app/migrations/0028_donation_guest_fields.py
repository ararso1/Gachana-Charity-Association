from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0027_backfill_existing_designation_modules'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='donor_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='donation',
            name='donor_first_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='donation',
            name='donor_last_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='donation',
            name='member',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='donations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
