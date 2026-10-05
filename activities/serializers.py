"""Serialización JSON del dominio (sin dependencias externas).

Convierte DTOs del service layer en diccionarios listos para ``JsonResponse``.
El adaptador MCP no usa este módulo: construye sus propias respuestas a
partir de los mismos DTOs.
"""

from typing import Any

from activities.services import Activity


def activity_to_dict(activity: Activity) -> dict[str, Any]:
    return {
        "id": activity.id,
        "title": activity.title,
        "description": activity.description,
        "available": activity.available,
        "seats": activity.seats,
        "capacity": activity.capacity,
    }
