from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('action', 'actor', 'content_type', 'object_id', 'created_at')
    list_filter   = ('action',)
    search_fields = ('actor__phone', 'note')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
