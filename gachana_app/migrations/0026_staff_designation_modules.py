from django.db import migrations, models


SEEDED_DESIGNATIONS = {
    'Executive Director': {
        'description': 'Full operational oversight across staff, members, donations, and website content.',
        'modules': [
            'members',
            'staff',
            'donations',
            'banks',
            'blogs',
            'vacancies',
            'gallery',
            'sponsors',
            'contacts',
            'settings',
        ],
    },
    'Finance Officer': {
        'description': 'Handles donation review, bank accounts, and financial records.',
        'modules': ['donations', 'banks'],
    },
    'Member Services Officer': {
        'description': 'Supports members, membership cards, and community giving records.',
        'modules': ['members', 'donations', 'settings'],
    },
    'Communications Officer': {
        'description': 'Manages public website stories, media, sponsors, and contact messages.',
        'modules': ['blogs', 'gallery', 'sponsors', 'contacts'],
    },
    'Program Coordinator': {
        'description': 'Coordinates field programs and public gallery updates.',
        'modules': ['gallery', 'blogs', 'members'],
    },
    'Human Resources Officer': {
        'description': 'Manages staff records, designations, and public vacancy posts.',
        'modules': ['staff', 'vacancies'],
    },
}


def seed_designations(apps, schema_editor):
    StaffDesignation = apps.get_model('gachana_app', 'StaffDesignation')
    StaffProfile = apps.get_model('gachana_app', 'StaffProfile')

    for title, data in SEEDED_DESIGNATIONS.items():
        designation, created = StaffDesignation.objects.get_or_create(
            title=title,
            defaults={
                'description': data['description'],
                'modules': data['modules'],
            },
        )
        if not created and not designation.modules:
            designation.description = designation.description or data['description']
            designation.modules = data['modules']
            designation.save(update_fields=['description', 'modules'])

    for profile in StaffProfile.objects.exclude(designation__isnull=True):
        profile.designations.add(profile.designation)


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0025_backfill_sponsor_visible_until'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffdesignation',
            name='modules',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Portal modules this designation can access.',
            ),
        ),
        migrations.AddField(
            model_name='staffprofile',
            name='designations',
            field=models.ManyToManyField(
                blank=True,
                related_name='staff_profiles',
                to='gachana_app.staffdesignation',
            ),
        ),
        migrations.RunPython(seed_designations, migrations.RunPython.noop),
    ]
