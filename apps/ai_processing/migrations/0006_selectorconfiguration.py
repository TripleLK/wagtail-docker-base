# Generated by Django 5.1.7 on 2025-05-16 12:21

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_processing', '0005_urlprocessingrequest_created_page_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SelectorConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Configuration Name')),
                ('description', models.TextField(blank=True, help_text='Brief description of what this selector configuration is for', verbose_name='Description')),
                ('selector_config', models.JSONField(help_text='JSON configuration for selectors (list of dictionaries with selector, name, note, and preserve_html fields)', verbose_name='Selector Configuration')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='selector_configurations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Selector Configuration',
                'verbose_name_plural': 'Selector Configurations',
                'ordering': ['name', '-created_at'],
            },
        ),
    ]
