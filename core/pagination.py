from rest_framework.pagination import PageNumberPagination,CursorPagination

class CustomLimitPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50

class MyCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'


def paginate_response(
    request,
    queryset,
    serializer_class,
    paginator_class,
    extra_data=None,
    context=None
):
    paginator = paginator_class()
    page = paginator.paginate_queryset(queryset, request)

    serializer = serializer_class(
        page,
        many=True,
        context=context or {"request": request}
    )

    response = paginator.get_paginated_response(serializer.data)

    if extra_data:
        response.data.update(extra_data)

    return response
