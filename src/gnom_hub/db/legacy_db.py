# legacy_db.py — Backward compatibility re-exports
# All functions have moved to dedicated repositories.
# These re-exports ensure existing consumers continue to work.

from gnom_hub.db.connection import (  # noqa: F401
    get_db_conn,
)
from gnom_hub.db.system_repo import (  # noqa: F401
    init_db, get_state_value, set_state_value,
    get_active_project, set_active_project,
    get_language, set_language,
    is_testing, log_audit_event, cleanup_old_data,
)
from gnom_hub.db.showbox_repo import (  # noqa: F401
    save_showbox_presentation, get_showbox_presentations,
    delete_showbox_presentation, get_showbox_presentation_by_name,
    get_active_showbox, set_active_showbox,
)
from gnom_hub.db.chat_repo import (  # noqa: F401
    add_chat_message, get_chat_history,
    get_agent_memories, count_agent_memories, add_agent_memory,
    update_memory_content, delete_memory_by_id, delete_agent_memories,
    search_memories, get_chat_count,
    clear_project_chat, delete_project_completely, clear_project_chat_by_sender,
)
from gnom_hub.db.agent_repo import (  # noqa: F401
    validate_agent_limit_db, create_agent_record, get_all_agents,
    agent_exists, set_agent_status, update_agent_status,
    delete_agent_by_id, delete_non_system_agents, delete_offline_agents,
    set_agent_role, update_agent_role_memory,
    register_agent_in_db, pulse_agent_alive,
    clear_agent_jobs, update_agent_active_job,
)
from gnom_hub.db.soul_repo import (  # noqa: F401
    save_soul_fact, add_to_soul_memory, get_relevant_facts,
)
