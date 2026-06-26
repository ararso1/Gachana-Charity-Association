from django.db import migrations


EXISTING_DESIGNATION_MODULES = {
    'Finance': ['donations', 'banks'],
    'Program Officer': ['gallery', 'blogs', 'members'],
}


def backfill_existing_designations(apps, schema_editor):
    StaffDesignation = apps.get_model('gachana_app', 'StaffDesignation')
    for title, modules in EXISTING_DESIGNATION_MODULES.items():
        StaffDesignation.objects.filter(title=title, modules=[]).update(modules=modules)


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0026_staff_designation_modules'),
    ]

    operations = [
        migrations.RunPython(backfill_existing_designations, migrations.RunPython.noop),
    ]
