from django.db import migrations, models
from django.utils.text import slugify


def populate_blog_slugs(apps, schema_editor):
    Blog = apps.get_model('gachana_app', 'Blog')
    used = set()
    for blog in Blog.objects.order_by('pk'):
        base = slugify(blog.title)[:250] or f'post-{blog.pk}'
        slug = base
        counter = 1
        while slug in used:
            slug = f'{base}-{counter}'
            counter += 1
        used.add(slug)
        blog.slug = slug
        blog.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0021_blog_media_type_and_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='slug',
            field=models.SlugField(blank=True, max_length=280, null=True),
        ),
        migrations.RunPython(populate_blog_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='blog',
            name='slug',
            field=models.SlugField(blank=True, max_length=280, unique=True),
        ),
    ]
