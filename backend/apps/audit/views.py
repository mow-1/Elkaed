from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models import User
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class   = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields   = ['actor', 'action']

    def get_queryset(self):
        qs = AuditLog.objects.select_related('actor').all()

        target = self.request.query_params.get('target')
        if target:
            qs = qs.filter(content_type=ContentType.objects.get_for_model(User), object_id=target)

        date_from = self.request.query_params.get('created_at__gte')
        date_to   = self.request.query_params.get('created_at__lte')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs

    def list(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)
