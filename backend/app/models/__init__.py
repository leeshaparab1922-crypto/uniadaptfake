"""Import every model module so Base.metadata is complete for Alembic
autogenerate and for `Base.metadata.create_all()` in tests."""

from app.models import (  # noqa: F401
    academic_structure,
    audit_log,
    auth_tokens,
    calendar,
    enrollment,
    student,
    subject,
    subject_instance,
    user,
)
