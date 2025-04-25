from django.forms.fields import CharField
from .widgets import CategoryTagWidget
from .models import CategoryTag

class CategoryTagField(CharField):
    widget = CategoryTagWidget
    
    def clean(self, value):
        if value:
            # Split the value list on commas and process each tag
            tag_list = [tag.strip() for tag in value.split(',') if tag.strip()]
            
            # Create or get tags
            result = []
            for tag_text in tag_list:
                if ':' in tag_text:
                    category, name = [part.strip() for part in tag_text.split(':', 1)]
                    tag, created = CategoryTag.objects.get_or_create(
                        category=category,
                        name=name
                    )
                    result.append(tag)
            
            return result
        return []