from django.db import models
from wagtail.models import Page, Orderable, ClusterableModel
from wagtail.admin.panels import FieldRowPanel, FieldPanel, InlinePanel
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtail.fields import RichTextField
from wagtail.search import index
from taggit.models import TaggedItemBase
from modelcluster.contrib.taggit import ClusterTaggableManager
from apps.categorized_tags.models import CategorizedPageTag
from apps.categorized_tags.forms import CategoryTagForm
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

class BasicPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body')
    ]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body")
    ]

class CartPage(Page):
    pass

class ContactPage(Page):
    pass

class HomePage(Page):
    """
    Home page model that displays a hero section, categories, featured products, and about section.
    """
    hero_title = models.CharField(
        max_length=255,
        default="Welcome to Triad Scientific",
        help_text="Title for the hero section"
    )
    
    hero_subtitle = models.CharField(
        max_length=255,
        default="Your trusted source for high-quality lab equipment and scientific supplies",
        help_text="Subtitle for the hero section"
    )
    
    about_title = models.CharField(
        max_length=255,
        default="About Triad Scientific",
        help_text="Title for the about section"
    )
    
    about_content = RichTextField(
        default="Triad Scientific has been a leading provider of laboratory equipment for over 20 years. "
                "We offer a comprehensive range of high-quality scientific instruments, supplies, and accessories.",
        help_text="Content for the about section"
    )
    
    about_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Image for the about section"
    )
    
    content_panels = Page.content_panels + [
        FieldPanel('hero_title'),
        FieldPanel('hero_subtitle'),
        FieldPanel('about_title'),
        FieldPanel('about_content'),
        FieldPanel('about_image'),
    ]
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        # Get featured lab equipment pages - just getting the first 3 for simplicity
        featured_products = LabEquipmentPage.objects.live().order_by('?')[:3]  # Random selection
        
        context['featured_products'] = featured_products
        
        return context

class MultiProductPage(Page):
    """
    A page that displays multiple lab equipment products with search and filtering options.
    """
    intro_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Title to display at the top of the page"
    )
    
    intro_text = RichTextField(
        blank=True,
        help_text="Introductory text to display at the top of the page"
    )
    
    search_fields = Page.search_fields + [
        index.SearchField('intro_title'),
        index.SearchField('intro_text'),
    ]
    
    content_panels = Page.content_panels + [
        FieldPanel('intro_title'),
        FieldPanel('intro_text'),
    ]
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        # Get all lab equipment pages
        equipment_pages = LabEquipmentPage.objects.live().order_by('title')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(equipment_pages, 12)  # Show 12 products per page
        
        try:
            equipment_pages = paginator.page(page)
        except PageNotAnInteger:
            equipment_pages = paginator.page(1)
        except EmptyPage:
            equipment_pages = paginator.page(paginator.num_pages)
        
        context['search_results'] = equipment_pages
        
        # Pass a flag to indicate these are not search results
        context['is_search_results'] = False
        
        return context

class Spec(ClusterableModel):
    spec_group = ParentalKey(
        'SpecGroup',
        related_name='specs',
    )
    key = models.CharField(
        max_length=128,
        help_text="What the specification is measuring (e.g. height)"
    )
    value = models.CharField(
        max_length=256,
        help_text="The value of the specification (e.g. 50in)"
    )

    panels = [
        FieldRowPanel([
            FieldPanel('key'),
            FieldPanel('value'),
        ])
    ]

class SpecGroup(ClusterableModel):
    name = models.CharField(
        max_length=128,
        help_text="The name of the specification group (e.g. dimensions, construction, electrical, etc.)"
    )

class EquipmentModelSpecGroup(SpecGroup):
    equipment_model = ParentalKey(
        'EquipmentModel',
        related_name='spec_groups',
    )

    panels = [
        FieldPanel('name'),
        InlinePanel('specs', label="Specifications"),
    ]

class LabEquipmentPageSpecGroup(SpecGroup):
    LabEquipmentPage = ParentalKey(
        'LabEquipmentPage',
        related_name='spec_groups',
    )

    panels = [
        FieldPanel( "name" ),
        InlinePanel('specs', label="Specifications"),
    ]

class EquipmentFeature(Orderable):
    """
    An orderable model for equipment features (non-pairs).
    Each equipment page can have multiple features.
    """
    page = ParentalKey(
        'LabEquipmentPage',
        related_name='features'
    )

    feature = models.CharField(
        max_length=255,
        help_text="A single equipment feature."
    )

    panels = [
        FieldPanel('feature'),
    ]

    def __str__(self):
        return self.feature

class EquipmentModel(ClusterableModel):
    page = ParentalKey(
        'LabEquipmentPage',
        related_name='models',
    )

    name = models.CharField(
        max_length=128,
        help_text="The name of the model"
    )

    model_number = models.CharField(
        max_length=32,
        help_text="The identification number of the model"
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('model_number'),
        InlinePanel('spec_groups', label="Specification Groups"),
    ]

    @property
    def merged_spec_groups(self):
        """
        Returns the merged spec groups for this model (default specs overridden
        by model-specific specs). This calls LabEquipmentPage.get_effective_spec_groups.
        """
        print(self.page.get_effective_spec_groups(self))
        return self.page.get_effective_spec_groups(self)

class LabEquipmentGalleryImage(Orderable):
    page = ParentalKey(
        'LabEquipmentPage',
        related_name='gallery_images',
        on_delete=models.CASCADE
    )

    # Field for uploaded image (internal)
    internal_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='+'
    )

    # Field for an external image URL
    external_image_url = models.URLField(
        "External image URL",
        blank=True,
        help_text="If provided, this will be used instead of an uploaded image."
    )

    # Flag to indicate if this is a fallback image (to avoid recursion in templates)
    is_fallback = models.BooleanField(default=False, editable=False)

    panels = [
        FieldPanel('internal_image'),
        FieldPanel('external_image_url'),
    ]

    def get_image_url(self):
        """
        Returns the URL to be used:
         - Prefer the internal image if it exists
         - Otherwise, use the external image URL
         - If neither is available, return None
        
        Note: External images are now used with an onerror handler in the template
        to fallback to a default image if the external URL has CORS issues.
        """
        if self.internal_image:
            # Prefer internal images as they won't have CORS issues
            rendition = self.internal_image.get_rendition('fill-800x600')
            return rendition.url
        elif self.external_image_url and not self.is_fallback:
            # External image - template will handle CORS issues with onerror
            return self.external_image_url
        return None

class LabEquipmentPage(Page):
    """
    A page model for a single lab equipment item.
    """
    short_description = RichTextField(
        blank=True,
        help_text="A brief summary of the equipment."
    )

    full_description = RichTextField(
        blank=True,
        help_text="Detailed description of the equipment."
    )

    # This field will store our custom tags
    # tags = ClusterTaggableManager(through=CategoryPageTag, blank=True)
    categorized_tags = ClusterTaggableManager(through=CategorizedPageTag, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('short_description', classname="full"),
        FieldPanel('full_description', classname="full"),
        FieldPanel('categorized_tags'),
        InlinePanel('gallery_images', label='Images'),
        InlinePanel(
            'spec_groups',
            label="Specification Groups",
            help_text="Technical specifications about the piece of equipment. "
            "You can provide default specs here which may be overridden for a particular model."
        ),
        InlinePanel('models', label='Models'),
    ]

    base_form_class = CategoryTagForm

    subpage_types = []  # No subpages allowed for a detail page

    class Meta:
        verbose_name = "Lab Equipment Page"

    def main_image(self):
        gallery_item = self.gallery_images.first()
        if gallery_item:
            return gallery_item.get_image_url
        else:
            return None

    @property
    def spec_group_names(self):
        print("getting spec_group_names")
        spec_group_names = set()
        for model in self.models.all():
            print("a model")
            spec_groups = self.get_effective_spec_groups(model)
            for spec_group in spec_groups:
                spec_group_names.add(spec_group['name'])

        print("returning: " + str(spec_group_names))
        return sorted(list(spec_group_names))

    def get_effective_spec_groups(self, equipment_model=None):
        """
        Returns a list of merged spec groups (each a dict with a name and a list of specs)
        If an equipment_model is passed, then any spec group in that model overrides the default.
        Otherwise, just the page-level spec groups are returned.
        """
        effective = {}

        # Gather all shared spec groups
        for group in self.spec_groups.all():
            effective[group.name] = {
                'name': group.name,
                'specs': list(group.specs.all())
            }

        # If a model is provided, override or add spec groups.
        if equipment_model:
            for group in equipment_model.spec_groups.all():
                if group.name in effective:
                    effective[group.name]['specs'] += list(group.specs.all())
                else:
                    effective[group.name] = {
                        'name': group.name,
                        'specs': list(group.specs.all())
                       }

        # Return as a list – you can sort by name or leave unsorted.
        return sorted(effective.values(), key=lambda x: x['name'])

class LabEquipmentAccessory(ClusterableModel):
    page = ParentalManyToManyField(
        'LabEquipmentPage',related_name='accessories',
    )
    image = models.ForeignKey(
        'wagtailimages.Image',
        related_name='+',
        on_delete=models.CASCADE
    )

    model_number = models.CharField(
        max_length=32,
        help_text="The identification number of the accessory"
    )

    name = models.CharField(
        max_length=32,
        help_text="The name of the accessory"
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('model_number'),
        FieldPanel('image'),
    ]
