"""Modelos del dominio de actividades.

Esta es la única fuente de verdad sobre actividades e inscripciones.
La API REST (``views.py``) y el adaptador MCP (``mcp_server/``) acceden a
estos datos únicamente a través del service layer (``services.py``):
nunca copian queries ni reglas de negocio.
"""

from django.db import models


class Activity(models.Model):
    """Una actividad con cupo limitado a la que pueden inscribirse estudiantes."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    capacity = models.PositiveIntegerField()
    seats_taken = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    @property
    def seats_free(self) -> int:
        return max(0, self.capacity - self.seats_taken)

    @property
    def is_available(self) -> bool:
        return self.is_active and self.seats_taken < self.capacity


class Registration(models.Model):
    """Inscripción de un estudiante en una actividad."""

    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="registrations"
    )
    student_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "student_email"],
                name="unique_registration_per_activity",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_email} -> {self.activity.title}"
