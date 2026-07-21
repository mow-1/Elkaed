from django.contrib.contenttypes.models import ContentType
from .models import AuditLog


def log_action(actor, action, target=None, before=None, after=None, note=''):
    """Append one row to the audit ledger. `target` may be None (system-level actions)."""
    content_type = ContentType.objects.get_for_model(target) if target is not None else None
    object_id = target.pk if target is not None else None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        content_type=content_type,
        object_id=object_id,
        before=before or {},
        after=after or {},
        note=note,
    )
