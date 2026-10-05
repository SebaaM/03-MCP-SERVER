"""Test de extremo a extremo del adaptador MCP por stdio.

Uso (con la DB en baseline):
    uv run python test_e2e.py

Deja filas de inscripción `e2e.*` en la DB: volvé al baseline con el comando
documentado en el README antes de re-ejecutarlo.
"""

import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT = Path(__file__).resolve().parent
PASS, FAIL = [], []


def check(label: str, condition: bool, detail: object = "") -> None:
    (PASS if condition else FAIL).append(label)
    print(f"[{'OK' if condition else 'FAIL'}] {label} {detail if not condition else ''}")


async def call(session: ClientSession, tool: str, args: dict):
    res = await session.call_tool(tool, args)
    if res.structured_content is not None:
        return res.structured_content.get("result", res.structured_content)
    if res.content:
        return json.loads(res.content[0].text)
    return {}


async def main() -> None:
    params = StdioServerParameters(command="uv", args=["run", "python", "server.py"], cwd=PROJECT)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            tools = await s.list_tools()
            names = {t.name for t in tools.tools}
            check("tools registradas", {"search_activities", "request_confirmation", "register_for_activity"} <= names, names)

            cat = await s.read_resource("activities://available")
            check("resource catálogo no vacío", any(c.text for c in cat.contents))
            det = await s.read_resource("activities://1")
            check("resource detalle 1", "Taller de robótica" in det.contents[0].text, det.contents[0].text)
            nf = await s.read_resource("activities://999")
            check("resource inexistente actionnable", "activity_not_found" in nf.contents[0].text, nf.contents[0].text)
            nan = await s.read_resource("activities://abc")
            check("resource id no numérico", "activity_not_found" in nan.contents[0].text, nan.contents[0].text)

            r_s = await call(s, "search_activities", {"query": "Cor", "only_available": True})
            check("search devuelve resultado", isinstance(r_s, list) and any("Coro" in d["title"] for d in r_s), r_s)

            email = "e2e.host@untdf.edu.ar"
            conf = await call(s, "request_confirmation", {"activity_id": "1", "student_email": email})
            token = conf.get("confirmation", "")
            check("request_confirmation emite token", conf.get("status") == "confirmation_issued" and len(token) == 32, conf)

            ok = await call(s, "register_for_activity", {"activity_id": "1", "student_email": email, "confirmation": token})
            check("registro OK", ok.get("status") == "registered", ok)

            again = await call(s, "register_for_activity", {"activity_id": "1", "student_email": email, "confirmation": token})
            check("token de un solo uso rechazado", again.get("status") == "confirmation_required", again)

            no = await call(s, "register_for_activity", {"activity_id": "1", "student_email": "e2e.b@untdf.edu.ar"})
            check("sin token -> confirmation_required", no.get("status") == "confirmation_required", no)
            invented = await call(s, "register_for_activity", {"activity_id": "1", "student_email": "e2e.b@untdf.edu.ar", "confirmation": "sí-ya-confirmo"})
            check("token inventado rechazado", invented.get("status") == "confirmation_required", invented)

            bad = await call(s, "request_confirmation", {"activity_id": "1", "student_email": "no-es-un-email"})
            check("request_confirmation email inválido", bad.get("status") == "invalid_email", bad)

            bad_id = await call(s, "register_for_activity", {"activity_id": "abc", "student_email": "e2e.b@untdf.edu.ar", "confirmation": "x"})
            check("activity_id no numérico", bad_id.get("status") == "invalid_activity_id", bad_id)

            c2 = await call(s, "request_confirmation", {"activity_id": "999", "student_email": "e2e.b@untdf.edu.ar"})
            t2 = c2.get("confirmation", "")
            nf2 = await call(s, "register_for_activity", {"activity_id": "999", "student_email": "e2e.b@untdf.edu.ar", "confirmation": t2})
            check("actividad inexistente", nf2.get("status") == "activity_not_found", nf2)

            c4 = await call(s, "request_confirmation", {"activity_id": "1", "student_email": email})
            t4 = c4.get("confirmation", "")
            dup = await call(s, "register_for_activity", {"activity_id": "1", "student_email": email, "confirmation": t4})
            check("doble inscripción", dup.get("status") == "already_registered", dup)

            c3 = await call(s, "request_confirmation", {"activity_id": "3", "student_email": "e2e.full@untdf.edu.ar"})
            t3 = c3.get("confirmation", "")
            full = await call(s, "register_for_activity", {"activity_id": "3", "student_email": "e2e.full@untdf.edu.ar", "confirmation": t3})
            check("cupo agotado", full.get("status") == "activity_full", full)

    print("\nRESULTADO:", len(PASS), "ok,", len(FAIL), "fallas")
    if FAIL:
        print("Fallaron:", FAIL)
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())