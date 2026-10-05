"""Vistas REST sobre el mismo service layer que usa el adaptador MCP."""

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from activities.serializers import activity_to_dict
from activities.services import (
    ActivityFull,
    ActivityNotFound,
    AlreadyRegistered,
    InvalidEmail,
    get_activity_service,
)


@require_GET
def activity_list(request: HttpRequest) -> JsonResponse:
    """GET /api/activities/ — catálogo de actividades disponibles."""
    service = get_activity_service()
    return JsonResponse(
        [activity_to_dict(item) for item in service.list_available()], safe=False
    )


@require_GET
def activity_detail(request: HttpRequest, activity_id: str) -> JsonResponse:
    """GET /api/activities/<id>/ — detalle de una actividad."""
    try:
        activity = get_activity_service().get_activity(activity_id)
    except ActivityNotFound:
        return JsonResponse(
            {"error": "activity_not_found", "activity_id": activity_id}, status=404
        )
    return JsonResponse(activity_to_dict(activity))


@require_GET
def activity_search(request: HttpRequest) -> JsonResponse:
    """GET /api/activities/search/?query=...[&only_available=false]."""
    query = request.GET.get("query", "")
    only_available = request.GET.get("only_available", "true").lower() != "false"
    results = get_activity_service().search(query, only_available)
    return JsonResponse([activity_to_dict(item) for item in results], safe=False)


@require_POST
def activity_register(request: HttpRequest, activity_id: str) -> JsonResponse:
    """POST /api/activities/<id>/register/ con JSON {"student_email": "..."}."""
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        result = get_activity_service().register(
            activity_id, payload.get("student_email", "")
        )
    except ActivityNotFound:
        return JsonResponse(
            {"error": "activity_not_found", "activity_id": activity_id}, status=404
        )
    except InvalidEmail as error:
        return JsonResponse({"error": "invalid_email", "message": str(error)}, status=400)
    except ActivityFull as error:
        return JsonResponse({"error": "activity_full", "message": str(error)}, status=409)
    except AlreadyRegistered as error:
        return JsonResponse(
            {"error": "already_registered", "message": str(error)}, status=409
        )
    return JsonResponse(result, status=201)
