"""Carga datos de ejemplo para probar la API REST y el adaptador MCP.

Uso:
    uv run python manage.py seed_activities
"""

from django.core.management.base import BaseCommand

from activities.models import Activity

EXAMPLES = [
    {
        "title": "Taller de robótica",
        "description": "Introducción a Arduino y sensores.",
        "capacity": 20,
        "seats_taken": 5,
        "is_active": True,
    },
    {
        "title": "Club de lectura",
        "description": "Literatura argentina contemporánea.",
        "capacity": 15,
        "seats_taken": 0,
        "is_active": True,
    },
    {
        "title": "Fútbol 5",
        "description": "Torneo interno de los viernes.",
        "capacity": 10,
        "seats_taken": 10,
        "is_active": True,
    },
    {
        "title": "Coro universitario",
        "description": "Temporada 2026, todos los niveles.",
        "capacity": 30,
        "seats_taken": 12,
        "is_active": True,
    },
    {
        "title": "Fotografía nocturna (archivada)",
        "description": "Edición pasada, ya finalizada.",
        "capacity": 12,
        "seats_taken": 3,
        "is_active": False,
    },
]


class Command(BaseCommand):
    help = "Crea actividades de ejemplo (idempotente por título)."

    def handle(self, *args, **options):
        created = 0
        for data in EXAMPLES:
            _, was_created = Activity.objects.get_or_create(
                title=data["title"], defaults=data
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(f"Listo: {created} nuevas, {len(EXAMPLES) - created} ya existían.")
        )
