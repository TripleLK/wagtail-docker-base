from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from .models import CategoryTag
from django.utils.html import format_html
from django.templatetags.static import static
from wagtail import hooks
import json

class CategoryTagViewSet(SnippetViewSet):
    model = CategoryTag
    menu_label = 'Categorized Tags'
    icon = 'tag'
    list_display = ('name', 'category', 'slug')
    list_filter = ('category',)
    search_fields = ('name', 'category')
    
    # Add ordering
    ordering = ['category', 'name']

register_snippet(CategoryTagViewSet)

@hooks.register('insert_global_admin_css')
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static('css/jquery.tagit.css'))

@hooks.register('insert_global_admin_js')
def global_admin_js():
    return format_html('<script src="{}"></script>', static('js/tag-it.min.js'))

@hooks.register('insert_editor_js')
def editor_js():
    return format_html(
        '<script>window.categoryTagCategories = {};</script>',
        json.dumps(list(CategoryTag.objects.values_list('category', flat=True).distinct()))
    )