# legacy_db.py — Backward compatibility re-exports
# All functions have moved to dedicated repositories.
# These re-exports ensure existing consumers continue to work.

from gnom_hub.db.agent_repo import (  # noqa: F401
    agent_exists,
    clear_agent_jobs,
    create_agent_record,
    delete_agent_by_id,
    delete_non_system_agents,
    delete_offline_agents,
    get_all_agents,
    pulse_agent_alive,
    register_agent_in_db,
    set_agent_role,
    set_agent_status,
    update_agent_active_job,
    update_agent_role_memory,
    update_agent_status,
    validate_agent_limit_db,
)
from gnom_hub.db.chat_repo import (  # noqa: F401
    add_agent_memory,
    add_chat_message,
    clear_project_chat,
    clear_project_chat_by_sender,
    count_agent_memories,
    delete_agent_memories,
    delete_memory_by_id,
    delete_project_completely,
    get_agent_memories,
    get_chat_count,
    get_chat_history,
    search_memories,
    update_memory_content,
)
from gnom_hub.db.connection import (  # noqa: F401
    get_db_conn,
)
from gnom_hub.db.showbox_repo import (  # noqa: F401
    delete_showbox_presentation,
    get_active_showbox,
    get_showbox_presentation_by_name,
    get_showbox_presentations,
    save_showbox_presentation,
    set_active_showbox,
)
from gnom_hub.db.soul_repo import (  # noqa: F401
    add_to_soul_memory,
    get_relevant_facts,
    save_soul_fact,
)
from gnom_hub.db.system_repo import (  # noqa: F401
    cleanup_old_data,
    get_active_project,
    get_language,
    get_state_value,
    init_db,
    is_testing,
    log_audit_event,
    set_active_project,
    set_language,
    set_state_value,
)
