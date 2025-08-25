from django.utils import timezone
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
try:
    from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
except Exception:  # drf-spectacular optional
    def extend_schema(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator
    class OpenApiParameter:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
    class OpenApiTypes:  # type: ignore
        STR = int
        INT = int

from .models import Visit, StudentVisit, STATUS_AWAITING_ARRIVAL, STATUS_CHECKED_IN, STATUS_CHECKED_OUT, STATUS_CANCELLED
from .serializers import VisitListSerializer, StudentVisitListSerializer


class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def apply_common_filters(qs, request):
    status_param = request.query_params.get('status')
    department_id = request.query_params.get('department_id')
    employee_id = request.query_params.get('employee_id')
    period = (request.query_params.get('period') or '').lower()  # today, 24h, 7d, 30d
    iin_last4 = request.query_params.get('guest_iin_last4')

    if status_param in {STATUS_AWAITING_ARRIVAL, STATUS_CHECKED_IN, STATUS_CHECKED_OUT, STATUS_CANCELLED}:
        qs = qs.filter(status=status_param)
    if department_id:
        try:
            qs = qs.filter(department_id=int(department_id))
        except ValueError:
            pass
    if employee_id and hasattr(Visit, 'employee_id'):
        try:
            qs = qs.filter(employee_id=int(employee_id))
        except ValueError:
            pass
    # Временной фильтр
    if period:
        now = timezone.now()
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            qs = qs.filter(entry_time__gte=start)
        elif period in ('24h', '1d'):
            qs = qs.filter(entry_time__gte=now - timezone.timedelta(hours=24))
        elif period in ('7d', 'week'):
            qs = qs.filter(entry_time__gte=now - timezone.timedelta(days=7))
        elif period in ('30d', 'month'):
            qs = qs.filter(entry_time__gte=now - timezone.timedelta(days=30))

    # Быстрый фильтр по последним 4 цифрам ИИН через связанный объект, если есть
    if iin_last4:
        qs = qs.filter(guest__iin_hash__isnull=False, guest__iin_encrypted__isnull=False)
        # Безопасный путь: хранить last4 в модели приглашения/группы, но здесь ограничимся по ФИО
        # Так как iin_last4 недоступен напрямую, пропускаем или можно добавить поиск по full_name как компромисс
    return qs


@extend_schema(tags=['visits'])
class VisitViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VisitListSerializer
    pagination_class = DefaultPagination

    @extend_schema(parameters=[
        OpenApiParameter(name='status', required=False, type=OpenApiTypes.STR, description='AWAITING|CHECKED_IN|CHECKED_OUT|CANCELLED'),
        OpenApiParameter(name='department_id', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='employee_id', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='period', required=False, type=OpenApiTypes.STR, description='today|24h|7d|30d'),
        OpenApiParameter(name='ordering', required=False, type=OpenApiTypes.STR, description='-entry_time|entry_time|-exit_time|exit_time'),
        OpenApiParameter(name='page', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='page_size', required=False, type=OpenApiTypes.INT),
    ])
    def list(self, request, *args, **kwargs):
        qs = (Visit.objects
              .select_related('guest', 'department', 'employee')
              .only('id', 'status', 'entry_time', 'exit_time', 'purpose', 'guest__full_name', 'department__name', 'employee__first_name', 'employee__last_name', 'employee__username'))
        qs = apply_common_filters(qs, request)

        ordering = request.query_params.get('ordering') or '-entry_time'
        allowed = {'entry_time', '-entry_time', 'exit_time', '-exit_time'}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=['student_visits'])
class StudentVisitViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentVisitListSerializer
    pagination_class = DefaultPagination

    @extend_schema(parameters=[
        OpenApiParameter(name='status', required=False, type=OpenApiTypes.STR, description='AWAITING|CHECKED_IN|CHECKED_OUT|CANCELLED'),
        OpenApiParameter(name='department_id', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='period', required=False, type=OpenApiTypes.STR, description='today|24h|7d|30d'),
        OpenApiParameter(name='ordering', required=False, type=OpenApiTypes.STR, description='-entry_time|entry_time|-exit_time|exit_time'),
        OpenApiParameter(name='page', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='page_size', required=False, type=OpenApiTypes.INT),
    ])
    def list(self, request, *args, **kwargs):
        qs = (StudentVisit.objects
              .select_related('guest', 'department')
              .only('id', 'status', 'entry_time', 'exit_time', 'purpose', 'guest__full_name', 'department__name'))
        qs = apply_common_filters(qs, request)

        ordering = request.query_params.get('ordering') or '-entry_time'
        allowed = {'entry_time', '-entry_time', 'exit_time', '-exit_time'}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


