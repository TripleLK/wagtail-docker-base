from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse

from wagtail.models import Page
from apps.base_site.models import LabEquipmentPage, MultiProductPage

# To enable logging of search queries for use with the "Promoted search results" module
# <https://docs.wagtail.org/en/stable/reference/contrib/searchpromotions.html>
# uncomment the following line and the lines indicated in the search function
# (after adding wagtail.contrib.search_promotions to INSTALLED_APPS):

# from wagtail.contrib.search_promotions.models import Query


def search(request):
    search_query = request.GET.get("query", None)
    page = request.GET.get("page", 1)

    # Search specifically for LabEquipmentPage
    if search_query:
        search_results = LabEquipmentPage.objects.live().search(search_query)

        # To log this query for use with the "Promoted search results" module:
        # query = Query.get(search_query)
        # query.add_hit()

    else:
        search_results = LabEquipmentPage.objects.none()

    # Pagination
    paginator = Paginator(search_results, 12)  # Show 12 products per page
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    # Get the MultiProductPage to use its template
    try:
        multi_product_page = MultiProductPage.objects.live().first()
    except MultiProductPage.DoesNotExist:
        multi_product_page = None

    # Process results to make sure we call main_image() as a method, not a property
    for result in search_results:
        # Ensure main_image is called as a method
        if hasattr(result, 'main_image') and callable(result.main_image):
            result.main_image_url = result.main_image()
        else:
            result.main_image_url = None

    return TemplateResponse(
        request,
        "base_site/multi_product_page.html",  # Use the MultiProductPage template
        {
            "page": multi_product_page,  # Pass the page for consistent template rendering
            "search_query": search_query,
            "search_results": search_results,
            "is_search_results": True,  # Flag to indicate these are search results
        },
    )
