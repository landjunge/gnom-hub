# Gnom-Hub Soul Feature Package
from gnom_hub.soul.soul import SoulAG, handle_user_feedback, run_evolution, soul_instance
from gnom_hub.soul.soul_initializer import SOULS, check_and_wait_breakpoint, get_soul
from gnom_hub.soul.zwc_soul import add_agent_metadata, add_directive, decode_soul, get_directives, strip_zwc

__all__ = [
    "SoulAG", "handle_user_feedback", "run_evolution", "soul_instance",
    "SOULS", "check_and_wait_breakpoint", "get_soul",
    "add_agent_metadata", "add_directive", "decode_soul", "get_directives", "strip_zwc",
]
