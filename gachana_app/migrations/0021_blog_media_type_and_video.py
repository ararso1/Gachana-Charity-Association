from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gachana_app', '0020_gallery_category_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='media_type',
            field=models.CharField(
                choices=[('image', 'Image'), ('video', 'Video')],
                default='image',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='blog',
            name='banner_video',
            field=models.FileField(blank=True, null=True, upload_to='blog_videos/'),
        ),
        migrations.AlterField(
            model_name='blog',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to='images/'),
        ),
    ]
