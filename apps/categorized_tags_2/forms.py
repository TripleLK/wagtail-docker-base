from django import forms
from taggit.forms import TagField
from wagtail.admin.forms import WagtailAdminPageForm
from .fields import CategoryTagField
import logging

# Get a logger to output debug info
logger = logging.getLogger(__name__)

class CategoryTagForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Replace the tag field with our custom one
        if 'categorized_tags' in self.fields:
            self.fields['categorized_tags'] = CategoryTagField(
                required=False,
                help_text=self.fields['categorized_tags'].help_text
            )
    
    def save_instance(self):
        # Get the tags from the cleaned data
        tags = self.cleaned_data.get('categorized_tags', [])
        
        # Log for debugging
        logger.info(f"Saving page with tags: {tags}")
        
        # First save the instance without tags to get an ID if it's new
        instance = super().save_instance()
        
        # Set the tags explicitly
        if hasattr(instance, 'categorized_tags') and tags:
            # Clear existing tags first
            instance.categorized_tags.clear()
            
            # Add each tag
            for tag in tags:
                instance.categorized_tags.add(tag)
            
            # Log the result
            logger.info(f"After saving, page has tags: {list(instance.categorized_tags.all())}")
        
        return instance
