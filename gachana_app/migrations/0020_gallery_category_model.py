from django.db import migrations, models
import django.db.models.deletion


LEGACY_GALLERY_CATEGORIES = [
    ('certifications', 'Certifications', 4),
    ('early_child_development', 'Early Child Development', 0),
    ('basic_educations', 'Basic Education', 1),
    ('youth_Development', 'Youth Development', 2),
    ('community_empowerment', 'Community Empowerment', 3),
]


def migrate_gallery_categories(apps, schema_editor):
    Gallery = apps.get_model('gachana_app', 'Gallery')
    GalleryCategory = apps.get_model('gachana_app', 'GalleryCategory')
    slug_to_category = {}
    for slug, name, sort_order in LEGACY_GALLERY_CATEGORIES:
        cat, _ = GalleryCategory.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'sort_order': sort_order, 'is_active': True},
        )
        slug_to_category[slug] = cat
    fallback = slug_to_category.get('community_empowerment') or next(iter(slug_to_category.values()), None)
    for item in Gallery.objects.all():
        legacy_slug = item.category_legacy
        cat = slug_to_category.get(legacy_slug) or fallback
        if cat:
            item.category_new_id = cat.id
            item.save(update_fields=['category_new_id'])


def reverse_gallery_categories(apps, schema_editor):
    Gallery = apps.get_model('gachana_app', 'Gallery')
    GalleryCategory = apps.get_model('gachana_app', 'GalleryCategory')
    for item in Gallery.objects.select_related('category_new').all():
        if item.category_new_id:
            item.category_legacy = item.category_new.slug
            item.save(update_fields=['category_legacy'])
    GalleryCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0019_staffprofile_can_manage_donations'),
    ]

    operations = [
        migrations.CreateModel(
            name='GalleryCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True, help_text='Inactive categories are hidden on the public gallery filters.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'gallery categories',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.RenameField(
            model_name='gallery',
            old_name='category',
            new_name='category_legacy',
        ),
        migrations.AddField(
            model_name='gallery',
            name='category_new',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='images',
                to='gachana_app.gallerycategory',
            ),
        ),
        migrations.RunPython(migrate_gallery_categories, reverse_gallery_categories),
        migrations.RemoveField(
            model_name='gallery',
            name='category_legacy',
        ),
        migrations.RenameField(
            model_name='gallery',
            old_name='category_new',
            new_name='category',
        ),
        migrations.AlterField(
            model_name='gallery',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='images',
                to='gachana_app.gallerycategory',
            ),
        ),
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['name'], 'verbose_name_plural': 'blog categories'},
        ),
        migrations.AlterModelOptions(
            name='gallery',
            options={'verbose_name_plural': 'gallery images'},
        ),
    ]
