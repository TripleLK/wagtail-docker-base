from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TagBase, ItemBase
from wagtail.models import Page
from modelcluster.contrib.taggit import ClusterTaggableManager
from wagtail.admin.panels import FieldPanel
from django.utils.text import slugify
class CategoryTag(TagBase):
    category = models.CharField(max_length=100)
    
    panels = [
        FieldPanel('category'),
        FieldPanel('name'),
    ]
    
    class Meta:
        verbose_name = "Category Tag"
        verbose_name_plural = "Category Tags"
        unique_together = ('name', 'category')
    
    def __str__(self):
        return f"{self.category}: {self.name}"
    
    def save(self, *args, **kwargs):
        # Generate the slug from category and name if not explicitly provided
        if not self.slug:
            self.slug = slugify(f"{self.category}-{self.name}")
        super().save(*args, **kwargs)

class CategoryTaggedItemBase(ItemBase):
    tag = models.ForeignKey(
        CategoryTag, related_name="tagged_items", on_delete=models.CASCADE
    )
    
    class Meta:
        abstract = True


class CategoryPageTag(CategoryTaggedItemBase):
    content_object = ParentalKey('base_site.LabEquipmentPage', on_delete=models.CASCADE, related_name='tagged_items')
