from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0022_blog_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('logo', models.ImageField(upload_to='sponsors/')),
                ('tagline', models.CharField(blank=True, help_text='Short line shown under the sponsor name (optional).', max_length=255)),
                ('website_url', models.URLField(blank=True, help_text='Optional link when visitors click the card.')),
                ('tier', models.CharField(choices=[('platinum', 'Platinum'), ('gold', 'Gold'), ('silver', 'Silver'), ('partner', 'Partner')], default='gold', max_length=20)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
    ]
