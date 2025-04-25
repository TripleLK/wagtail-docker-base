from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categorized_tags_2', '0005_create_tag_categories'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CategoryTag',
            new_name='CategorizedTag',
        ),
        migrations.RenameModel(
            old_name='CategoryPageTag',
            new_name='CategorizedPageTag',
        ),
    ] 