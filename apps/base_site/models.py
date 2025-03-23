from django.db import models
from wagtail.models import Page, Orderable
from wagtail.admin.panels import FieldPanel, InlinePanel
from modelcluster.fields import ParentalKey

from wagtail.fields import RichTextField
from wagtail.search import index


class BasicPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body')
    ]

    content_panels = Page.content_panels + ["intro", "body"]


class LabEquipmentPage(Page):
    """
    A page model for a single lab equipment item.
    """
    # Use the built-in .title field for the equipment name.
    short_description = RichTextField(
        blank=True,
        help_text="A brief summary of the equipment."
    )

    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Main image for the equipment."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price of the equipment."
    )
    description = RichTextField(
        blank=True,
        help_text="Detailed description of the equipment."
    )

    content_panels = Page.content_panels + [
        FieldPanel('short_description', classname="full"),
        FieldPanel('main_image'),
        FieldPanel('price'),
        FieldPanel('description', classname="full"),
        InlinePanel('specifications', label="Specifications"),
    ]

    # Optionally limit what pages can host this one.
    subpage_types = []  # No subpages allowed for a detail page

    class Meta:
        verbose_name = "Lab Equipment Page"


class EquipmentSpecification(Orderable):
    """
    An orderable model for equipment specifications.
    Each equipment page can have multiple specifications.
    """
    page = ParentalKey(
        'LabEquipmentPage',
        related_name='specifications'
    )
    specification = models.CharField(
        max_length=255,
        help_text="A single specification detail."
    )

    panels = [
        FieldPanel('specification'),
    ]

    def __str__(self):
        return self.specification
