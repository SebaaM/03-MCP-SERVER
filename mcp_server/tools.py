"""Tools: capacidades que el host puede pedir ejecutar.

TRABAJO DEL ALUMNO: implementar las functions de este módulo delegando en el
service layer (``activities.services``). No exponer SQL, ORM ni views como
parte del contrato MCP. Los errores del dominio se convierten en resultados
accionables (dicts con ``status`` y ``message``).

La inscripción requiere una confirmación emitida por el host a través de
``request_confirmation``; ``register_for_activity`` nunca acepta un booleano
que el modelo pueda inventar (ver ``confirmations.is_host_confirmation_valid``).
"""

from mcp.server import MCPServer

from activities.services import (
    Activity,
    ActivityFull,
    ActivityNotFound,
    AlreadyRegistered,
    InvalidEmail,
    get_activity_service,
)
from mcp_server.confirmations import (
    CONFIRMATION_TTL_SECONDS,
    audit,
    consume_confirmation,
    is_host_confirmation_valid,
    issue_confirmation,
)

MAX_QUERY_LENGTH = 100


def _as_dict(activity: Activity) -> dict[str, object]:
    """Convierte el DTO del service layer en un dict apto para MCP.

    Evita exponer el objeto ORM o el service layer como contrato.
    Campos: id, title, available, seats (nada sensible).
    """
    return {
        "id": activity.id,
        "title": activity.title,
        "available": activity.available,
        "seats": activity.seats,
    }


def _normalize_query(query: str) -> str:
    """Limpia la query: recorta y limita la longitud a MAX_QUERY_LENGTH."""
    return str(query or "").strip()[:MAX_QUERY_LENGTH]


def _validated_activity_id(activity_id: str) -> tuple[str, dict[str, str] | None]:
    """Valida y normaliza el ID. Devuelve (valor, error)."""
    value = str(activity_id or "").strip()
    if not value:
        return value, {
            "status": "invalid_activity_id",
            "message": "activity_id es obligatorio.",
        }
    if not value.isdigit():
        return value, {
            "status": "invalid_activity_id",
            "message": f"El ID de actividad debe ser numérico, recibí {activity_id!r}.",
        }
    return value, None


def _validated_email(student_email: str) -> tuple[str, dict[str, str] | None]:
    """Valida y normaliza el correo (trim + minúsculas). Devuelve (valor, error)."""
    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.core.validators import validate_email

    value = str(student_email or "").strip().lower()
    if not value:
        return value, {
            "status": "invalid_email",
            "message": "student_email es obligatorio.",
        }
    try:
        validate_email(value)
    except DjangoValidationError:
        return value, {
            "status": "invalid_email",
            "message": f"El correo no es válido: {student_email!r}.",
        }
    return value, None


def register_tools(mcp: MCPServer) -> None:
    @mcp.tool()
    def search_activities(query: str = "", only_available: bool = True) -> list[dict[str, object]]:
        """Busca actividades por título y, opcionalmente, sólo entre las disponibles."""
        service = get_activity_service()
        results = service.search(_normalize_query(query), only_available)
        return [_as_dict(activity) for activity in results]

    @mcp.tool()
    def request_confirmation(activity_id: str, student_email: str) -> dict[str, str]:
        """Emite una confirmación por el host para una inscripción pendiente.

        Devuelve un token opaco de un solo uso. Es el host (interfaz) quien
        debe mostrarlo y pedir la confirmación explícita del estudiante.
        """
        activity_id, error = _validated_activity_id(activity_id)
        if error:
            return error
        email, error = _validated_email(student_email)
        if error:
            return error

        token = issue_confirmation(activity_id, email)
        audit("request_confirmation", activity_id, email, "confirmation_issued", token)
        return {
            "status": "confirmation_issued",
            "confirmation": token,
            "activity_id": activity_id,
            "student_email": email,
            "ttl_seconds": str(CONFIRMATION_TTL_SECONDS),
            "message": (
                "Mostrale este código de confirmación al estudiante y ejecutá "
                "register_for_activity con él sólo si confirma la inscripción."
            ),
        }

    @mcp.tool()
    def register_for_activity(
        activity_id: str, student_email: str, confirmation: str = ""
    ) -> dict[str, str]:
        """Inscribe a un estudiante en una actividad.

        Requiere el token de confirmación emitido previamente por
        ``request_confirmation`` (confirmación del host, no un booleano).
        """
        activity_id, error = _validated_activity_id(activity_id)
        if error:
            return error
        email, error = _validated_email(student_email)
        if error:
            return error

        token = str(confirmation or "").strip()
        if not is_host_confirmation_valid(token, activity_id, email):
            audit("register", activity_id, email, "confirmation_required", token)
            return {
                "status": "confirmation_required",
                "activity_id": activity_id,
                "message": (
                    "Falta una confirmación válida del host. Usá request_confirmation "
                    "para emitir el código y mostrarlo al estudiante antes de inscribir."
                ),
            }

        service = get_activity_service()
        try:
            result = service.register(activity_id, email)
        except ActivityNotFound as exc:
            audit("register", activity_id, email, "activity_not_found", token)
            return {
                "status": "activity_not_found",
                "activity_id": str(exc),
                "message": f"No existe la actividad con ID `{exc}`.",
            }
        except InvalidEmail as exc:
            audit("register", activity_id, email, "invalid_email", token)
            return {"status": "invalid_email", "message": str(exc)}
        except ActivityFull as exc:
            audit("register", activity_id, email, "activity_full", token)
            return {
                "status": "activity_full",
                "activity_id": activity_id,
                "message": str(exc),
            }
        except AlreadyRegistered as exc:
            audit("register", activity_id, email, "already_registered", token)
            return {
                "status": "already_registered",
                "activity_id": activity_id,
                "message": str(exc),
            }

        consume_confirmation(token)
        audit("register", activity_id, email, "registered", token)
        return result