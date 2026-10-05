"""Confirmaciones emitidas por el host y registro de auditoría.

Una inscripción sólo se ejecuta si el host ya emitió una confirmación con la
tool ``request_confirmation`` (respuesta que el estudiante confirma en la
interfaz). La tool ``register_for_activity`` NO acepta un booleano que el
modelo pueda inventar: exige el token opaco emitido por el host, de un solo
uso y con vencimiento.

No copia reglas del dominio: sólo resuelve "¿quién confirmó?" y registra qué
se hizo. La doble inscripción la evita el constraint único de Django
(``ActivityService.register`` + ``AlreadyRegistered``); acá se evita el doble
uso del mismo token.
"""

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CONFIRMATION_TTL_SECONDS = 600
AUDIT_FILE = Path(__file__).resolve().parent / "audit.log"


@dataclass
class ConfirmationRecord:
    token: str
    activity_id: str
    student_email: str
    issued_at: float
    consumed: bool = False


@dataclass
class AuditEvent:
    timestamp: str
    action: str
    activity_id: str
    student_email: str
    outcome: str
    confirmation_hash: str


class ConfirmationIssuer:
    """Emite y valida confirmaciones de un solo uso firmadas por el host."""

    def __init__(self, ttl_seconds: int = CONFIRMATION_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._records: dict[str, ConfirmationRecord] = {}
        self._lock = threading.Lock()

    def issue(self, activity_id: str, student_email: str) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._records[token] = ConfirmationRecord(
                token=token,
                activity_id=activity_id,
                student_email=student_email,
                issued_at=time.time(),
            )
        return token

    def is_valid(
        self,
        confirmation: object,
        activity_id: str,
        student_email: str,
    ) -> bool:
        """El token existe, no fue usado, no venció y corresponde al par dado."""
        if not isinstance(confirmation, str) or not str(confirmation).strip():
            return False
        with self._lock:
            record = self._records.get(confirmation)
            if record is None:
                return False
            if record.consumed:
                return False
            if time.time() - record.issued_at > self._ttl_seconds:
                return False
            return (
                record.activity_id == activity_id
                and record.student_email == student_email
            )

    def consume(self, confirmation: str) -> ConfirmationRecord | None:
        """Marca el token como usado. Devuelve None si ya no es válido."""
        with self._lock:
            record = self._records.get(confirmation)
            if record is None or record.consumed:
                return None
            record.consumed = True
            return record


class AuditLog:
    """Registro en memoria de las operaciones sensibles (inscripciones)."""

    def __init__(self, path: Path = AUDIT_FILE) -> None:
        self._events: list[AuditEvent] = []
        self._lock = threading.Lock()
        self._path = path

    def add(
        self,
        action: str,
        activity_id: str,
        student_email: str,
        outcome: str,
        confirmation: object = None,
    ) -> None:
        digest = ""
        if isinstance(confirmation, str) and confirmation:
            digest = hashlib.sha256(confirmation.encode("utf-8")).hexdigest()
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            activity_id=activity_id,
            student_email=student_email,
            outcome=outcome,
            confirmation_hash=digest,
        )
        with self._lock:
            self._events.append(event)
            try:
                line = json.dumps(
                    {
                        "timestamp": event.timestamp,
                        "action": event.action,
                        "activity_id": event.activity_id,
                        "student_email": event.student_email,
                        "outcome": event.outcome,
                        "confirmation_hash": event.confirmation_hash,
                    },
                    ensure_ascii=False,
                )
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except OSError:
                # La auditoría no debe romper la operación de inscripción.
                pass

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


# Singletons del adaptador (estado del servidor MCP, no del dominio).
_confirmation_issuer = ConfirmationIssuer()
_audit_log = AuditLog()


def is_host_confirmation_valid(
    confirmation: object,
    activity_id: str,
    student_email: str,
) -> bool:
    """Una confirmación es válida sólo si fue emitida por el host.

    No acepta booleanos ni valores adivinables: sólo el token opaco de un uso
    emitido por ``request_confirmation`` para esa actividad y correo.
    """
    return _confirmation_issuer.is_valid(confirmation, activity_id, student_email)


def issue_confirmation(activity_id: str, student_email: str) -> str:
    return _confirmation_issuer.issue(activity_id, student_email)


def consume_confirmation(confirmation: str) -> ConfirmationRecord | None:
    return _confirmation_issuer.consume(confirmation)


def audit(action: str, activity_id: str, student_email: str, outcome: str, confirmation: object = None) -> None:
    _audit_log.add(action, activity_id, student_email, outcome, confirmation)


def audit_count() -> int:
    return len(_audit_log)