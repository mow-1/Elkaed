ADMIN_ROLES = ('admin', 'staff')
OPS_ROLES = ('admin', 'staff', 'assistant')


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role in ADMIN_ROLES)


def is_ops(user) -> bool:
    return bool(user and user.is_authenticated and user.role in OPS_ROLES)
