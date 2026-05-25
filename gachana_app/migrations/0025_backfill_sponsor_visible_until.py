from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def backfill_visible_until(apps, schema_editor):
    Sponsor = apps.get_model('gachana_app', 'Sponsor')
    preset_days = {
        'one_week': 7,
        'one_month': 30,
        'three_months': 90,
        'six_months': 180,
        'one_year': 365,
    }
    today = timezone.localdate()
    for sponsor in Sponsor.objects.filter(visible_until__isnull=True).exclude(visibility_preset='lifetime'):
        days = preset_days.get(sponsor.visibility_preset, 365)
        sponsor.visible_until = today + timedelta(days=days)
        sponsor.save(update_fields=['visible_until'])


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0024_sponsor_visibility'),
    ]

    operations = [
        migrations.RunPython(backfill_visible_until, migrations.RunPython.noop),
    ]
