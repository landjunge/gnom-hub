"""tests/test_router.py — Unit Tests für den Router (router.py)"""

from unittest.mock import patch


class TestGetObedienceInstructions:
    def test_level_1_blindly_follows(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(1)
        assert "BLINDLY" in result
        assert "hinterfrage nichts" in result.lower()

    def test_level_3_balanced(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(3)
        assert "BALANCED" in result
        assert "ausgewogenes" in result.lower()

    def test_level_5_highly_autonomous(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(5)
        assert "HIGHLY AUTONOMOUS" in result
        assert "eigenständig" in result.lower()

    def test_level_2_strongly_follows(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(2)
        assert "STRONGLY" in result

    def test_level_4_cautious(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(4)
        assert "CAUTIOUS" in result

    def test_invalid_level_falls_back_to_balanced(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(99)
        assert "BALANCED" in result

    def test_zero_level_falls_back_to_balanced(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(0)
        assert "BALANCED" in result

    def test_negative_level_falls_back_to_balanced(self):
        from gnom_hub.core.prompt.builder import _get_obedience_instructions
        result = _get_obedience_instructions(-1)
        assert "BALANCED" in result


class TestGetBehavioralInstructions:
    def test_default_settings_returns_empty(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({})
        assert result == ""

    def test_formal_personality_included(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"personality": 1})
        assert "formal" in result.lower()

    def test_casual_personality_included(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"personality": 5})
        assert "casual" in result.lower()

    def test_detailed_response_style(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"response_style": 5})
        assert "detailed" in result.lower() or "exhaustive" in result.lower()

    def test_concise_response_style(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"response_style": 1})
        assert "concise" in result.lower()

    def test_safety_risk_tolerance(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"risk_tolerance": 1})
        assert "safety" in result.lower()
        assert "robustness" in result.lower()

    def test_bold_risk_tolerance(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"risk_tolerance": 5})
        assert "bold" in result.lower()

    def test_professional_personality(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"personality": 2})
        assert "professional" in result.lower()

    def test_warm_personality(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"personality": 4})
        assert "warm" in result.lower()

    def test_unknown_personality_value_ignored(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"personality": 99})
        assert result == ""

    def test_combined_settings_all_applied(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({
            "personality": 1, "response_style": 5, "risk_tolerance": 4
        })
        assert "VERHALTENS-INSTRUKTIONEN" in result
        assert "formal" in result.lower()
        assert "detailed" in result.lower() or "exhaustive" in result.lower()
        assert "innovative" in result.lower()

    def test_irrelevant_settings_ignored(self):
        from gnom_hub.core.prompt.builder import _get_behavioral_instructions
        result = _get_behavioral_instructions({"foo": "bar", "baz": 42})
        assert result == ""


class TestGetAgentRole:
    def test_known_agent_returns_role(self):
        from gnom_hub.infrastructure.router.router import _get_agent_role
        with patch("gnom_hub.agents.agent_definitions.AGENT_DEFINITIONS",
                   {"coderag": {"role": "coder"}}):
            result = _get_agent_role("coderag")
        assert result == "coder"

    def test_unknown_agent_returns_empty(self):
        from gnom_hub.infrastructure.router.router import _get_agent_role
        result = _get_agent_role("nonexistent")
        assert result == ""

    def test_empty_name_returns_empty(self):
        from gnom_hub.infrastructure.router.router import _get_agent_role
        result = _get_agent_role("")
        assert result == ""

    def test_agent_without_role_returns_empty(self):
        from gnom_hub.infrastructure.router.router import _get_agent_role
        with patch("gnom_hub.agents.agent_definitions.AGENT_DEFINITIONS",
                   {"coderag": {}}):
            result = _get_agent_role("coderag")
        assert result == ""


class TestResolve:
    def test_auto_provider_uses_smart_router(self):
        from gnom_hub.infrastructure.router.router import _resolve
        with patch("gnom_hub.infrastructure.router.router.SmartRouter.resolve_stage_candidates",
                   return_value=[("openrouter", "gpt-4")]):
            result = _resolve("auto", "stage_3", {}, "coderag")
        assert result == [("openrouter", "gpt-4")]

    def test_lokal_provider_returns_lokal(self):
        from gnom_hub.infrastructure.router.router import _resolve
        result = _resolve("lokal", "llama3", {}, "coderag")
        assert result == [("lokal", "llama3")]

    def test_openrouter_provider_uses_working_models(self):
        from gnom_hub.infrastructure.router.router import _resolve
        with patch("gnom_hub.infrastructure.router.router.Config.OPENROUTER_FREE_MODELS",
                   ["gpt-4", "claude-3"]):
            with patch("gnom_hub.infrastructure.router.router.SQLiteStateRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_value.return_value = ["gpt-4", "claude-3"]
                candidates = _resolve("openrouter", "gpt-4", {}, "coderag")
        assert len(candidates) >= 1
        providers = [c[0] for c in candidates]
        assert "openrouter" in providers

    def test_named_provider_falls_back_to_openrouter_with_lokal(self):
        from gnom_hub.infrastructure.router.router import _resolve
        with patch("gnom_hub.infrastructure.router.router.Config.OPENROUTER_FREE_MODELS",
                   ["gpt-4"]):
            with patch("gnom_hub.infrastructure.router.router.SQLiteStateRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_value.return_value = ["gpt-4"]
                candidates = _resolve("anthropic", "claude-3", {}, "coderag")
        providers = [c[0] for c in candidates]
        assert "anthropic" in providers
        assert "openrouter" in providers
        assert ("lokal", "llama3") in candidates

    def test_unknown_provider_still_returns_candidate(self):
        from gnom_hub.infrastructure.router.router import _resolve
        result = _resolve("unknown_provider", "some-model", {}, "coderag")
        assert len(result) >= 1
        assert ("lokal", "llama3") in result

    def test_openrouter_without_working_models_uses_defaults(self):
        from gnom_hub.infrastructure.router.router import _resolve
        with patch("gnom_hub.infrastructure.router.router.Config.OPENROUTER_FREE_MODELS",
                   ["gpt-4"]):
            with patch("gnom_hub.infrastructure.router.router.SQLiteStateRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_value.return_value = []
                candidates = _resolve("openrouter", "other-model", {}, "coderag")
        providers = [c[0] for c in candidates]
        assert "openrouter" in providers


class TestBuildSys:
    def test_no_agent_name_returns_error_marker(self):
        """Phase-2: ohne agent_name baut der Builder mit Default 'Agent'.
        config/agents/Agent.json existiert nicht → Error-Marker statt Crash.
        """
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value", return_value={}):
            result = _build_sys("coderag", "original sys", None)
        assert isinstance(result, str)
        assert "⚠️ FEHLER" in result

    def test_obedience_injected(self):
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value", return_value={}):
            result = _build_sys("coderag", "sys", "CoderAG")
        assert "=== OBEDIENCE" in result

    def test_custom_prompt_appended(self):
        """Phase-2: custom_prompt und preset_prompt werden via
        _apply_post_processing in builder.py an den Prompt angehängt.
        Patches zielen auf die Source-Module (builder macht lazy imports)."""
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value") as mock_gsv:
            def side_effect(key, default=None):
                if key == "agent_settings":
                    return {"coderag": {"custom_prompt": "CUSTOM SUFFIX"}}
                if key == "active_preset":
                    return "Web Development"
                return default
            mock_gsv.side_effect = side_effect
            with patch("gnom_hub.core.utils.preset_service.get_preset_prompt", return_value="PRESET"):
                with patch("gnom_hub.core.utils.evolution_v2.get_active_version", return_value=None):
                    result = _build_sys("coderag", "sys", "CoderAG")
        assert "CUSTOM SUFFIX" in result
        assert "PRESET" in result

    def test_sys_prompt_override_removed(self):
        """Phase-2: REGRESSION-TEST — der versteckte sys_prompt-Override ist
        ENTFERNT. Settings mit sys_prompt-Key dürfen NICHT den System-Prompt
        ersetzen. Stattdessen kommt der JSON-Identity-Text aus config/agents.
        """
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value") as mock_gsv:
            def side_effect(key, default=None):
                if key == "agent_settings":
                    return {"coderag": {"sys_prompt": "OVERRIDDEN SYS"}}
                if key == "active_preset":
                    return ""  # kein preset prefix
                return default
            mock_gsv.side_effect = side_effect
            with patch("gnom_hub.core.utils.evolution_v2.get_active_version", return_value=None):
                result = _build_sys("coderag", "original sys", "CoderAG")
        assert "OVERRIDDEN SYS" not in result, (
            "REGRESSION: sys_prompt-Override-Pfad ist zurück! Sollte in Phase 2 entfernt sein."
        )
        # Stattdessen kommt der JSON-Identity-Text
        assert "CoderAG" in result

    def test_slider_error_does_not_crash(self):
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value", return_value={}):
            with patch("gnom_hub.core.utils.slider_prompt.build_system_prompt",
                       side_effect=Exception("Slider kaputt")):
                result = _build_sys("coderag", "sys", "CoderAG")
        assert isinstance(result, str)
        assert "OBEDIENCE" in result

    def test_evolution_rules_injected(self):
        """Phase-3: evolution rules sind Context-Fetcher in context.py.
        Mockt den Fetcher direkt (statt get_active_version) weil sonst
        allowed_contexts-Filterung den Aufruf verhindert."""
        from gnom_hub.infrastructure.router.router import _build_sys
        with patch("gnom_hub.infrastructure.router.router.get_state_value", return_value={}):
            with patch("gnom_hub.core.prompt.context._get_evolution_rules",
                       return_value="[KONTEXT:evolution_rules]\n=== SELBSTVERBESSERTE REGELN ===\n- Regel 1\n- Regel 2"):
                result = _build_sys("generalag", "sys", "GeneralAG")
        assert "Regel 1" in result
        assert "Regel 2" in result
        assert "SELBSTVERBESSERTE REGELN" in result
