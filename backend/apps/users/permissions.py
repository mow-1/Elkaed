ADMIN_ROLES = ('admin', 'staff')
OPS_ROLES = ('admin', 'staff', 'assistant')


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role in ADMIN_ROLES)


def is_ops(user) -> bool:
    return bool(user and user.is_authenticated and user.role in OPS_ROLES)


def is_course_owner(user, course) -> bool:
    if is_admin(user):
        return True
    return bool(user and user.is_authenticated and user.role == 'instructor' and course.instructor_id == user.id)
