from django import forms
from django.template.loader import render_to_string
from taggit.forms import TagWidget
from .models import CategoryTag
import logging

# Set up logging
logger = logging.getLogger(__name__)

class CategoryTagWidget(TagWidget):
    template_name = 'categorized_tags_2/widgets/category_tag_widget.html'
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # If value is a list of objects, convert to strings
        if value and isinstance(value, (list, tuple)) and hasattr(value[0], 'category'):
            # The value is a list of CategoryTag objects
            value_strings = [f"{tag.category}: {tag.name}" for tag in value]
            context['widget']['value'] = value_strings
            
            logger.info(f"Setting widget value to: {value_strings}")
        
        # Add existing tags for the autocomplete
        existing_tags = [
            {'id': tag.id, 'text': f"{tag.category}: {tag.name}"} 
            for tag in CategoryTag.objects.all()
        ]
        context['widget']['existing_tags'] = existing_tags
        
        # Get existing categories for category dropdown
        context['widget']['categories'] = CategoryTag.objects.values_list(
            'category', flat=True
        ).distinct().order_by('category')
        
        # Log for debugging
        logger.info(f"Widget context: value={value}, tags count={len(existing_tags)}")
        
        return context
