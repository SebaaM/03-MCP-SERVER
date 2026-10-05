"""Prompts: flujos guiados reutilizables que el host puede invocar.

TRABAJO DEL ALUMNO: implementar el prompt de este módulo.
A diferencia de un resource (contexto legible) o una tool (acción que el
modelo decide ejecutar), un prompt empaqueta un flujo completo en mensajes
listos para el modelo: qué resources/tools usar y en qué orden.
No copia reglas de negocio: sólo orquesta las capacidades ya expuestas.
"""

from mcp.server import MCPServer


def register_prompts(mcp: MCPServer) -> None:
    @mcp.prompt(
        description="Guía al estudiante paso a paso: explorar, elegir e inscribirse en una actividad."
    )
    def guia_inscripcion(query: str = "", student_email: str = "") -> list[dict[str, object]]:
        """Flujo guiado de inscripción a actividades.

        Args:
            query: tema o palabra clave de interés (ej. "robótica").
                Vacío = mostrar todo el catálogo.
            student_email: correo del estudiante, si ya se conoce.
                Vacío = el modelo debe pedirlo antes de inscribir.
        """
        tiene_query = bool(str(query or "").strip())
        tiene_email = bool(str(student_email or "").strip())

        aprendizaje = "el estudiante filtraría por tema"
        if tiene_query:
            aprendizaje = f"el estudiante busca `{query}`"
        email = "te lo voy a pedir en la confirmación"
        if tiene_email:
            email = f"ya conozco el correo: `{student_email}`"

        instruccion = (
            "Sos la guía de inscripción a actividades de la UNTDF. Ayudás a un "
            "estudiante a explorar, elegir e inscribirse. NO inscribas por tu "
            "cuenta: seguí este flujo, en este orden, y no avances sin completar "
            "cada paso.\n\n"
            f"Contexto: {aprendizaje}. Sobre el correo: {email}.\n\n"
            "1. **Explorar el catálogo**: leé el resource `activities://available` "
            "y presentá las actividades con cupo (título, ID y cupos).\n"
            "2. **Buscar por tema**: usá la tool `search_activities` con "
            "`query` y `only_available=True` para filtrar por el interés del "
            "estudiante. Si ya eligió una del catálogo, podés saltear este paso.\n"
            "3. **Ver detalle**: cuando elija una actividad, leé el resource "
            "`activities://{activity_id}` (reemplazá el ID) y mostrale el detalle "
            "completo: título, estado, cupos y descripción. No decida sin esto.\n"
            "4. **Confirmación y email**: pedí confirmación explícita de la "
            "elección y el correo del estudiante. No sigas sin ambos.\n"
            "5. **Confirmar por el host**: usá la tool `request_confirmation` con "
            "el `activity_id` y el `student_email` elegidos. Mostrale el código "
            "de confirmación al estudiante y pedile que lo apruebe. No inventes "
            "el código ni un 'confirmado' verbal: la tool emite el token del host."
            "\n"
            "6. **Inscribir**: usá la tool `register_for_activity` con el "
            "`activity_id`, el `student_email` y el `confirmation` (el código "
            "emitido) y comunicá el resultado. Si falla (confirmación inválida, "
            "actividad inexistente, sin cupo, ya inscripto o email inválido), "
            "contá el motivo y proponé una alternativa o emití de nuevo la "
            "confirmación.\n\n"
            "Cerrá resumiendo la inscripción (actividad y correo) o qué sigue."
        )

        return [
            {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "text": (
                        "Buenas, soy la guía de inscripción a actividades. "
                        "Recorremos juntos el catálogo, vemos el detalle de la que "
                        "te interese y, recién con tu confirmación y correo, te inscribo."
                    ),
                },
            },
            {"role": "user", "content": {"type": "text", "text": instruccion}},
        ]
