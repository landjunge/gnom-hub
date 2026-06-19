# pvm_compare.py
def compare_versions(pvm, version_id_1: str, version_id_2: str) -> dict:
    v1 = pvm.get_version_by_id(version_id_1)
    v2 = pvm.get_version_by_id(version_id_2)
    if not v1 or not v2: return {"diff": "Version not found"}
    added = list(set(v2.modifications) - set(v1.modifications))
    removed = list(set(v1.modifications) - set(v2.modifications))
    return {
        "v1_id": version_id_1, "v2_id": version_id_2,
        "v1_score": v1.performance_score, "v2_score": v2.performance_score,
        "added_rules": added, "removed_rules": removed,
        "prompt_changed": v1.base_prompt != v2.base_prompt
    }
