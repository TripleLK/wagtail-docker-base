# myapp/wagtail_hooks.py

from django.templatetags.static import static
from django.utils.safestring import mark_safe
from wagtail import hooks

@hooks.register('insert_global_admin_js')
def labequipment_editor_js():
    return mark_safe(f'<script src="{static('admin/js/labequipment_controller.js')}"></script>')
