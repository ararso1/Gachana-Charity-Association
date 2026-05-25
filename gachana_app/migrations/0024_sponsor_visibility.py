from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0023_sponsor'),
    ]

    operations = [
        migrations.AddField(
            model_name='sponsor',
            name='visibility_preset',
            field=models.CharField(
                choices=[
                    ('one_week', 'One week'),
                    ('one_month', 'One month'),
                    ('three_months', 'Three months'),
                    ('six_months', 'Six months'),
                    ('one_year', 'One year'),
                    ('lifetime', 'Lifetime'),
                    ('custom', 'Custom date'),
                ],
                default='one_year',
                help_text='How long this sponsor stays on the public website.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='sponsor',
            name='visible_until',
            field=models.DateField(
                blank=True,
                help_text='Last day shown on the site (inclusive). Leave empty for lifetime.',
                null=True,
            ),
        ),
    ]
