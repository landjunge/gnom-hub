from fastapi import APIRouter
from . import (
    memory_crud, memory_search, agents_list, agents_status, nudge, registry,
    chat_legacy, audio, admin_tools, admin_system, admin_config, workspace,
    llm_keys, llm_agents, llm_models, system_info, showbox, admin, metrics, integrity, workflows, observability,
    presets,
)

router = APIRouter()
# presets.router MUSS vor agents_status.router registriert werden, damit die
# neuen ``/api/presets``-Routen den Legacy-Endpoint in ``agents_status.py``
# überschreiben (FastAPI: "first registered wins" bei Path-Kollisionen).
for r in [
    presets.router,
    memory_crud.router, memory_search.router, agents_list.router, agents_status.router,
    nudge.router, registry.router, chat_legacy.router, audio.router, admin_tools.router,
    admin_system.router, admin_config.router, workspace.router, llm_keys.router,
    llm_agents.router, llm_models.router, system_info.router, showbox.router, admin.router,
    metrics.router, integrity.router, workflows.router, observability.router,
]:
    router.include_router(r)

