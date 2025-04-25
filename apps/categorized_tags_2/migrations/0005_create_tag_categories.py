from django.db import migrations
import random

def generate_random_color():
    h = random.randint(0, 360)
    s = 65
    l = 75
    return f"hsl({h}, {s}%, {l}%)"

def forward_migration(apps, schema_editor):
    """Create TagCategory objects for existing category strings"""
    CategoryTag = apps.get_model('categorized_tags_2', 'CategoryTag')
    TagCategory = apps.get_model('categorized_tags_2', 'TagCategory')
    
    # Get all unique category strings
    category_names = set()
    for tag in CategoryTag.objects.all():
        category_names.add(tag.category)
    
    # Create a TagCategory for each unique category
    for name in category_names:
        TagCategory.objects.get_or_create(
            name=name,
            defaults={'color': generate_random_color()}
        )

def reverse_migration(apps, schema_editor):
    """Delete all TagCategory objects"""
    TagCategory = apps.get_model('categorized_tags_2', 'TagCategory')
    TagCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('categorized_tags_2', '0004_tagcategory_remove_categorytag_color'),
    ]

    operations = [
        migrations.RunPython(forward_migration, reverse_migration),
    ] 