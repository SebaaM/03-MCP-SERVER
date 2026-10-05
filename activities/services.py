"""Service layer del dominio de actividades.

Esta es la única puerta de entrada a la lógica de negocio: las views REST
y las tools/resources MCP delegan en ``ActivityService`` y no copian
queries ni reglas. Ya está implementado: no hay que modificarlo para
completar la práctica, el trabajo está en ``mcp_server/``.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from activities.models import Activity as ActivityModel
from activities.models import Registration as RegistrationModel


class ActivityNotFound(Exception):
    """La actividad solicitada no existe."""


class ActivityFull(Exception):
    """La actividad ya no tiene cupos disponibles."""


class AlreadyRegistered(Exception):
    """El estudiante ya está inscripto en la actividad."""


class InvalidEmail(Exception):
    """El correo informado no es válido."""


class RegistrationNotImplemented(Exception):
    """Compatibilidad con el esqueleto inicial: ya no se usa.

    La inscripción está implementada en :meth:`ActivityService.register`.
    Se conserva el nombre para no romper importes existentes.
    """


@dataclass
class Activity:
    id: str
    title: str
    description: str
    available: bool
    seats: int
    capacity: int


def _to_dto(obj: ActivityModel) -> Activity:
    return Activity(
        id=str(obj.pk),
        title=obj.title,
        description=obj.description,
        available=obj.is_available,
        seats=obj.seats_free,
        capacity=obj.capacity,
    )


def _coerce_id(activity_id: str) -> int:
    try:
        return int(str(activity_id).strip())
    except (TypeError, ValueError):
        raise ActivityNotFound(activity_id) from None


def _normalize_email(student_email: str) -> str:
    value = str(student_email or "").strip().lower()
    try:
        validate_email(value)
    except DjangoValidationError:
        raise InvalidEmail(f"student_email debe ser un correo válido: {student_email!r}") from None
    return value


class ActivityService:
    """Casos de uso sobre actividades e inscripciones."""

    def list_available(self) -> list[Activity]:
        queryset = ActivityModel.objects.filter(is_active=True).order_by("title")
        return [_to_dto(obj) for obj in queryset if obj.is_available]

    def get_activity(self, activity_id: str) -> Activity:
        try:
            obj = ActivityModel.objects.get(pk=_coerce_id(activity_id))
        except ActivityModel.DoesNotExist:
            raise ActivityNotFound(activity_id) from None
        return _to_dto(obj)

    def search(self, query: str, only_available: bool = True) -> list[Activity]:
        queryset = ActivityModel.objects.all().order_by("title")
        text = str(query or "").strip()
        if text:
            queryset = queryset.filter(title__icontains=text)
        results = [_to_dto(obj) for obj in queryset]
        if only_available:
            results = [item for item in results if item.available]
        return results

    def register(self, activity_id: str, student_email: str) -> dict[str, str]:
        email = _normalize_email(student_email)
        with transaction.atomic():
            try:
                activity = ActivityModel.objects.select_for_update().get(
                    pk=_coerce_id(activity_id)
                )
            except ActivityModel.DoesNotExist:
                raise ActivityNotFound(activity_id) from None
            if not activity.is_available:
                raise ActivityFull(f"La actividad `{activity.title}` no tiene cupos.")
            try:
                RegistrationModel.objects.create(activity=activity, student_email=email)
            except IntegrityError:
                raise AlreadyRegistered(
                    f"{email} ya está inscripto en `{activity.title}`."
                ) from None
            activity.seats_taken += 1
            activity.save(update_fields=["seats_taken"])
        return {
            "status": "registered",
            "activity_id": str(activity.pk),
            "student_email": email,
        }


def get_activity_service() -> ActivityService:
    """Punto único de acceso al service layer."""
    return ActivityService()
