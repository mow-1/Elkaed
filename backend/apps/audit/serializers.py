from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor       = serializers.SerializerMethodField()
    target_repr = serializers.SerializerMethodField()

    class Meta:
        model  = AuditLog
        fields = ('id', 'actor', 'action', 'before', 'after', 'note', 'target_repr', 'created_at')

    def get_actor(self, obj):
        if not obj.actor_id:
            return None
        return {'id': obj.actor.id, 'phone': obj.actor.phone, 'full_name': obj.actor.full_name}

    def get_target_repr(self, obj):
        return str(obj.target) if obj.target else None
