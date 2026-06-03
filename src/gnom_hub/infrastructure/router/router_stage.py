from ...core.config import Config
from .router_config import DS_KEY, OR_KEY


class SmartRouter:
    """Kostenoptimiertes Auto-Routing – verwendet die Stufen aus Config und verifiziert API Keys."""

    ROLE_PREFERENCE = {
        "coder": "stage_4",
        "security": "stage_4",
        "researcher": "stage_4",
        "writer": "stage_3",
        "editor": "stage_3",
        "soul": "stage_3",
        "normal": "stage_3",
        "brainstorm": "stage_2",
        "default": "stage_3",
    }

    @staticmethod
    def get_stage_for_role(role: str) -> str:
        return SmartRouter.ROLE_PREFERENCE.get(role.lower(), "stage_3")

    @staticmethod
    def _order_working_models(working: list) -> list:
        from gnom_hub.core.config import Config
        curated = [m for m in Config.OPENROUTER_FREE_MODELS if m in working]
        others = [m for m in working if m not in Config.OPENROUTER_FREE_MODELS]
        return curated + others

    @staticmethod
    def get_best_openrouter_model(role: str) -> str:
        try:
            from gnom_hub.db.state_repo import SQLiteStateRepository
            repo = SQLiteStateRepository()
            working = repo.get_value("openrouter_working_models") or []
        except Exception:
            working = []
        if not working:
            working = list(Config.OPENROUTER_FREE_MODELS)
        
        working = SmartRouter._order_working_models(working)
            
        role = (role or "normal").lower()
        if role == "coder":
            for m in working:
                if any(x in m.lower() for x in ("coder", "qwen")):
                    return m
        elif role == "researcher":
            for m in working:
                if any(x in m.lower() for x in ("reasoning", "thinking", "trinity", "nemotron")):
                    return m
        elif role in ("writer", "editor"):
            for m in working:
                if any(x in m.lower() for x in ("poolside", "laguna", "llama")):
                    return m
        elif role == "soul":
            for m in working:
                if any(x in m.lower() for x in ("poolside", "liquid", "glm")):
                    return m
                    
        return working[0] if working else "meta-llama/llama-3.3-70b-instruct:free"

    @staticmethod
    def get_best_model(stage: str, available_models: list) -> str:
        preferred = {
            "stage_4": ["claude-3-5-sonnet-20241022", "claude-3.5-sonnet", "gpt-4o", "deepseek-reasoner", "gemini-1.5-pro"],
            "stage_3": ["deepseek-chat", "gemini-1.5-flash", "gpt-4o-mini", "mistral-large-latest", "llama-3.1-8b-instruct", "llama3.1"],
            "stage_2": ["meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen3-coder:free", "nousresearch/hermes-3-llama-3.1-405b:free", "google/gemma-4-31b-it:free", "meta-llama/llama-3.2-3b-instruct:free", "liquid/lfm-2.5-1.2b-instruct:free", "openai/gpt-oss-120b:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "poolside/laguna-xs.2:free", "poolside/laguna-m.1:free", "llama3", "gemma2"],
            "stage_1": ["llama3", "phi3", "mistral"]
        }.get(stage, ["llama3"])

        # Try finding stage preferred models
        for m in preferred:
            if any(m.lower() in am.lower() for am in available_models):
                for am in available_models:
                    if m.lower() in am.lower():
                        return am

        # Fallback: check against Config.OPENROUTER_FREE_MODELS
        for model in Config.OPENROUTER_FREE_MODELS:
            if any(model.lower() in am.lower() for am in available_models):
                for am in available_models:
                    if model.lower() in am.lower():
                        return am

        return available_models[0] if available_models else "llama3"

    @staticmethod
    def is_provider_valid(provider: str, kdb: dict) -> bool:
        if any(k.get("provider") == provider and k.get("valid") for k in kdb.values()):
            return True
        if provider == "deepseek" and DS_KEY:
            return True
        if provider == "openrouter" and OR_KEY:
            return True
        return False

    @staticmethod
    def resolve_role_from_name(agent_name: str) -> str:
        name_lower = (agent_name or "").lower()
        if "coder" in name_lower:
            return "coder"
        elif "writer" in name_lower:
            return "writer"
        elif "editor" in name_lower:
            return "editor"
        elif "researcher" in name_lower:
            return "researcher"
        elif "security" in name_lower or "watchdog" in name_lower:
            return "security"
        elif "soul" in name_lower:
            return "soul"
        return "normal"

    @staticmethod
    def get_best_specific_assignment(role: str, kdb: dict, force_provider: str = None) -> tuple:
        """Determines the best specific provider and model for a role based on valid keys."""
        try:
            from gnom_hub.db.state_repo import SQLiteStateRepository
            repo = SQLiteStateRepository()
            working_models = repo.get_value("openrouter_working_models") or []
        except Exception:
            working_models = []
        if not working_models:
            working_models = list(Config.OPENROUTER_FREE_MODELS)
        working_models = SmartRouter._order_working_models(working_models)

        if force_provider:
            has_anthropic = (force_provider == "anthropic")
            has_openai = (force_provider == "openai")
            has_gemini = (force_provider == "gemini")
            has_deepseek = (force_provider == "deepseek")
            has_openrouter = (force_provider == "openrouter")
            has_mistral = (force_provider == "mistral")
        else:
            has_anthropic = any(k.get("provider") == "anthropic" and k.get("valid") for k in kdb.values())
            has_openai = any(k.get("provider") == "openai" and k.get("valid") for k in kdb.values())
            has_gemini = any(k.get("provider") == "gemini" and k.get("valid") for k in kdb.values())
            has_deepseek = any(k.get("provider") == "deepseek" and k.get("valid") for k in kdb.values())
            has_openrouter = any(k.get("provider") == "openrouter" and k.get("valid") for k in kdb.values())
            has_mistral = any(k.get("provider") == "mistral" and k.get("valid") for k in kdb.values())
        
        role = (role or "normal").lower()
        
        # 1. CODER / SECURITY
        if role in ("coder", "security"):
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-20241022"
            if has_deepseek:
                return "deepseek", "deepseek-reasoner"
            if has_openai:
                return "openai", "gpt-4o"
            if has_gemini:
                return "gemini", "gemini-1.5-pro"
            if has_mistral:
                return "mistral", "codestral-latest"
            if has_openrouter:
                for m in working_models:
                    if any(x in m.lower() for x in ("coder", "qwen", "llama-3.3", "codestral")):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"
            
        # 2. RESEARCHER
        elif role == "researcher":
            if has_deepseek:
                return "deepseek", "deepseek-reasoner"
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-20241022"
            if has_openai:
                return "openai", "gpt-4o"
            if has_gemini:
                return "gemini", "gemini-1.5-pro"
            if has_openrouter:
                for m in working_models:
                    if any(x in m.lower() for x in ("reasoning", "thinking", "trinity", "nemotron", "deepseek")):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"
            
        # 3. WRITER / EDITOR
        elif role in ("writer", "editor"):
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-20241022"
            if has_openai:
                return "openai", "gpt-4o-mini"
            if has_deepseek:
                return "deepseek", "deepseek-chat"
            if has_gemini:
                return "gemini", "gemini-1.5-flash"
            if has_openrouter:
                for m in working_models:
                    if any(x in m.lower() for x in ("poolside", "laguna", "llama")):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"
            
        # 4. SOUL
        elif role == "soul":
            if has_deepseek:
                return "deepseek", "deepseek-chat"
            if has_gemini:
                return "gemini", "gemini-1.5-flash"
            if has_openai:
                return "openai", "gpt-4o-mini"
            if has_openrouter:
                for m in working_models:
                    if any(x in m.lower() for x in ("liquid", "glm", "poolside", "gemma")):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "gemma2"
            
        # 5. GENERAL / NORMAL / OTHERS
        else:
            if has_deepseek:
                return "deepseek", "deepseek-chat"
            if has_gemini:
                return "gemini", "gemini-1.5-flash"
            if has_openai:
                return "openai", "gpt-4o-mini"
            if has_openrouter:
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"

    @staticmethod
    def get_stage_options(stage: str, role: str) -> list:
        or_model = SmartRouter.get_best_openrouter_model(role)
        role_lower = (role or "normal").lower()
        
        # Customize s4 options based on role (deepseek-reasoner is premium for coding/security/research)
        if role_lower in ("coder", "researcher", "security"):
            s4 = [
                ("anthropic", "claude-3-5-sonnet-20241022"),
                ("deepseek", "deepseek-reasoner"),
                ("openai", "gpt-4o"),
                ("gemini", "gemini-1.5-pro")
            ]
        else:
            s4 = [
                ("anthropic", "claude-3-5-sonnet-20241022"),
                ("openai", "gpt-4o"),
                ("gemini", "gemini-1.5-pro"),
                ("deepseek", "deepseek-chat")
            ]
            
        s3 = [
            ("deepseek", "deepseek-chat"),
            ("gemini", "gemini-1.5-flash"),
            ("openrouter", or_model),
            ("openai", "gpt-4o-mini"),
            ("mistral", "mistral-large-latest")
        ]
        s2 = [
            ("openrouter", or_model),
            ("deepseek", "deepseek-chat")
        ]
        s1 = [
            ("lokal", "llama3"),
            ("lokal", "mistral")
        ]

        if stage == "stage_4":
            return s4 + s3 + s2 + s1
        elif stage == "stage_3":
            return s3 + s2 + s1
        elif stage == "stage_2":
            return s2 + s1
        else:
            return s1

    @staticmethod
    def resolve_stage(stage: str, kdb: dict, agent_name: str) -> tuple:
        """Löst die Stufe in Provider + Modell auf (erster gültiger Kandidat)."""
        cands = SmartRouter.resolve_stage_candidates(stage, kdb, agent_name)
        return cands[0] if cands else ("lokal", "llama3")

    @staticmethod
    def resolve_stage_candidates(stage: str, kdb: dict, agent_name: str) -> list:
        """Gibt ALLE gültigen Provider+Modell-Kandidaten zurück (für Fallback-Kette)."""
        role = SmartRouter.resolve_role_from_name(agent_name)
        options = SmartRouter.get_stage_options(stage, role)
        seen = set()
        candidates = []
        for pvd, mdl in options:
            key = (pvd, mdl)
            if key not in seen and (pvd == "lokal" or SmartRouter.is_provider_valid(pvd, kdb)):
                seen.add(key)
                candidates.append((pvd, mdl))
        if not candidates:
            candidates.append(("lokal", "llama3"))
        return candidates

    @staticmethod
    def get_routing_insights(kdb: dict, current_agents: dict = None) -> list:
        """Erzeugt intelligente Empfehlungen und Begründungen für jeden Agenten."""
        insights = []
        # Get active agents from database if not supplied
        if not current_agents:
            from gnom_hub.db.state_repo import SQLiteStateRepository
            current_agents = SQLiteStateRepository().get_value("llm_agents", {})
            
        from gnom_hub.db.agent_repo import SQLiteAgentRepository
        db_agents = SQLiteAgentRepository().get_all()
        
        for a in db_agents:
            name_lower = a.name.lower()
            conf = current_agents.get(name_lower, {"provider": "auto", "model": "stage_3"})
            p_sel = conf.get("provider", "auto")
            m_sel = conf.get("model", "stage_3")
            
            # Resolve actual provider/model if "auto"
            resolved_p, resolved_m = p_sel, m_sel
            if p_sel == "auto":
                resolved_p, resolved_m = SmartRouter.resolve_stage(m_sel, kdb, a.name)
                
            role = a.role or SmartRouter.resolve_role_from_name(a.name)
            opt_p, opt_m = SmartRouter.get_best_specific_assignment(role, kdb)
            
            # Determine status and explanation
            status = "optimal"
            actionable = False
            explanation = ""
            
            def p_name(p):
                return {"deepseek": "DeepSeek", "openrouter": "OpenRouter", "openai": "OpenAI", 
                        "anthropic": "Anthropic", "gemini": "Gemini", "mistral": "Mistral", 
                        "lokal": "Lokal"}.get(p, p.capitalize())
            
            if resolved_p == opt_p and resolved_m == opt_m:
                status = "optimal"
                if opt_p == "lokal":
                    explanation = f"Nutzt das lokale Modell {opt_m}. Fügen Sie einen API-Key hinzu, um leistungsfähigere Modelle freizuschalten."
                elif role in ("coder", "security"):
                    explanation = f"Optimal zugewiesen! {p_name(opt_p)} ({opt_m}) bietet die höchste logische Präzision für Programmier- und Sicherheitsaufgaben."
                elif role == "researcher":
                    explanation = f"Optimal zugewiesen! {p_name(opt_p)} ({opt_m}) ist exzellent für strukturierte Websuche und logische Analysen."
                elif role in ("writer", "editor"):
                    explanation = f"Optimal zugewiesen! {p_name(opt_p)} ({opt_m}) liefert hervorragende Texterstellung und stilistische Präzision."
                elif role == "soul":
                    explanation = f"Optimal zugewiesen! {p_name(opt_p)} ({opt_m}) eignet sich ideal für kreative Dialoge und interaktiven Chat."
                else:
                    explanation = f"Optimal zugewiesen! {p_name(opt_p)} ({opt_m}) ist ein vielseitiges Allround-Modell für diese Rolle."
            else:
                tier = {"anthropic": 4, "deepseek": 4, "openai": 4, "gemini": 3, "mistral": 3, "openrouter": 2, "lokal": 1}
                opt_tier = tier.get(opt_p, 1)
                res_tier = tier.get(resolved_p, 1)
                
                if opt_tier > res_tier:
                    status = "upgrade_available"
                    actionable = True
                    explanation = f"Ein aktiver Key für ein besseres Modell ({p_name(opt_p)} - {opt_m}) wurde erkannt. Aktualisieren Sie, um die Leistung von {a.name} zu maximieren."
                elif opt_p != resolved_p or opt_m != resolved_m:
                    status = "manual_override"
                    explanation = f"Manueller Override aktiv: {p_name(resolved_p)} ({resolved_m}) wird verwendet. Das empfohlene Modell für diese Rolle ist {p_name(opt_p)} ({opt_m})."
                else:
                    explanation = f"Zugewiesen auf {p_name(resolved_p)} ({resolved_m})."
                    
            insights.append({
                "agent": a.name,
                "role": role,
                "current_provider": p_sel,
                "current_model": m_sel,
                "resolved_provider": resolved_p,
                "resolved_model": resolved_m,
                "optimal_provider": opt_p,
                "optimal_model": opt_m,
                "status": status,
                "explanation": explanation,
                "actionable": actionable
            })
            
        return insights
