from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    """
    Custom pagination class that allows client to control page size.
    Default: 20 items
    Max: 1000 items
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000
