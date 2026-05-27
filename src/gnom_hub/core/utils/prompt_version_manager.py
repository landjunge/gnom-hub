# prompt_version_manager.py — Version control for agent prompts
from typing import List, Optional
from gnom_hub.evolution.evolution_v2 import PromptVersion
import gnom_hub.evolution.pvm_create as pc
import gnom_hub.evolution.pvm_activate as pa
import gnom_hub.evolution.pvm_history as ph
import gnom_hub.evolution.pvm_rollback as pr
import gnom_hub.evolution.pvm_compare as pcomp
import gnom_hub.evolution.pvm_test as pt

class PromptVersionManager:
    def __init__(self, db=None): self.db = db
    def create_version(self, agent: str, prompt: str, modifications: List[str]) -> PromptVersion:
        return pc.create_version(agent, prompt, modifications)
    def activate_version(self, agent: str, version_id: str):
        pa.activate_version(agent, version_id)
    def record_test_result(self, version_id: str, success: bool):
        pt.record_test_result(version_id, success)
    def get_version_history(self, agent: str, limit: int = 10) -> List[PromptVersion]:
        return ph.get_version_history(agent, limit)
    def get_version_by_id(self, version_id: str) -> Optional[PromptVersion]:
        return ph.get_version_by_id(version_id)
    def should_rollback(self, agent: str, cur_id: str, prev_id: str) -> bool:
        return pr.should_rollback(self, agent, cur_id, prev_id)
    def auto_rollback(self, agent: str, prev_id: str):
        pr.auto_rollback(self, agent, prev_id)
    def compare_versions(self, version_id_1: str, version_id_2: str) -> dict:
        return pcomp.compare_versions(self, version_id_1, version_id_2)
