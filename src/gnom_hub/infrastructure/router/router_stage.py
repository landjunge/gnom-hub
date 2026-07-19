from gnom_hub.core.config import Config

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

    # Robust, hand-picked keyword matchers — kept narrow to avoid relying on
    # discontinued providers (poolside, lagune, nemotron, …). New OpenRouter
    # free models should fall back to the first curated entry instead of dying
    # silently in fragile string-match code.
    _ROLE_KEYWORDS = {
        "coder":      ("qwen", "coder", "codestral", "deepseek-coder"),
        "researcher": ("reasoning", "thinking", "trinity", "deepseek-r1"),
        "writer":     ("llama", "gemma", "mistral"),
        "editor":     ("llama", "gemma", "mistral"),
        "soul":       ("llama", "gemma", "liquid"),
    }

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
        keywords = SmartRouter._ROLE_KEYWORDS.get(role)
        if keywords:
            for m in working:
                ml = m.lower()
                if any(k in ml for k in keywords):
                    return m

        # llama-3.3-70b-instruct:free is permanently 404 (paid-only slug).
        # Default free pool entry is openrouter/free.
        return working[0] if working else "openrouter/free"

    # Curated, currently-shipped model names per stage. Kept conservative so we
    # never hand back a model that the providers have retired. New variants are
    # matched via substring (e.g. "gpt-4o" matches "gpt-4o-2024-08-06").
    _STAGE_PREFERRED = {
        # Top tier — premium cloud providers
        "stage_4": [
            "claude-3-5-sonnet", "claude-sonnet-4", "claude-3-opus",
            "gpt-4o", "o1",
            "deepseek-reasoner", "deepseek-chat",
            "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-pro",
        ],
        # Mid tier — fast + cheap cloud + good OpenRouter free
        "stage_3": [
            "deepseek-chat", "gemini-1.5-flash", "gpt-4o-mini",
            "mistral-large-latest", "codestral-latest",
            "llama-3.1-8b-instruct",
        ],
        # Free tier — OpenRouter free models + decent Ollama
        # (llama-3.3-70b-instruct:free removed: permanent 404, paid-only)
        "stage_2": [
            "openrouter/free",
            "tencent/hy3:free",
            "qwen/qwen3-coder:free",
            "google/gemma-3-27b-it:free",
            "openai/gpt-oss-120b:free",
            "arcee-ai/trinity-large-thinking:free",
            "meta-llama/llama-3.2-3b-instruct:free",
        ],
        # Local Ollama — always available, no network roundtrip
        "stage_1": ["qwen2.5-coder:7b", "llama3", "mistral", "phi3", "gemma2", "codellama"],
    }

    @staticmethod
    def get_best_model(stage: str, available_models: list) -> str:
        """Pick the best available model for the given stage.

        Resolution order:
          1. Curated stage-preferred list (substring-match against available).
          2. ``Config.OPENROUTER_FREE_MODELS`` (substring-match).
          3. First available model.
          4. Ollama default ``qwen2.5-coder:7b`` so the caller never starves.
        """
        preferred = SmartRouter._STAGE_PREFERRED.get(
            stage, SmartRouter._STAGE_PREFERRED["stage_1"]
        )

        # 1. Stage-preferred substring match
        for m in preferred:
            ml = m.lower()
            for am in available_models or []:
                if ml in am.lower():
                    return am

        # 2. OpenRouter free models as a softer fallback
        for model in Config.OPENROUTER_FREE_MODELS:
            ml = model.lower()
            for am in available_models or []:
                if ml in am.lower():
                    return am

        # 3. Whatever is left in available_models
        if available_models:
            return available_models[0]

        # 4. Final Ollama default — never starve the caller
        return "qwen2.5-coder:7b"

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
            has_minimax = (force_provider == "minimax")
        else:
            has_anthropic = any(k.get("provider") == "anthropic" and k.get("valid") for k in kdb.values())
            has_openai = any(k.get("provider") == "openai" and k.get("valid") for k in kdb.values())
            has_gemini = any(k.get("provider") == "gemini" and k.get("valid") for k in kdb.values())
            has_deepseek = any(k.get("provider") == "deepseek" and k.get("valid") for k in kdb.values())
            has_openrouter = any(k.get("provider") == "openrouter" and k.get("valid") for k in kdb.values())
            has_mistral = any(k.get("provider") == "mistral" and k.get("valid") for k in kdb.values())
            has_minimax = any(k.get("provider") == "minimax" and k.get("valid") for k in kdb.values())
        
        role = (role or "normal").lower()

        # MiniMax hat höchste Priorität wenn erzwungen oder verfügbar
        if has_minimax:
            return "minimax", "MiniMax-M3"

        # 1. CODER / SECURITY — high-precision tier
        if role in ("coder", "security"):
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-latest"
            if has_deepseek:
                return "deepseek", "deepseek-reasoner"
            if has_openai:
                return "openai", "gpt-4o"
            if has_gemini:
                return "gemini", "gemini-2.5-pro"
            if has_mistral:
                return "mistral", "codestral-latest"
            if has_openrouter:
                keywords = ("coder", "qwen", "llama-3.3", "codestral")
                for m in working_models:
                    if any(x in m.lower() for x in keywords):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "qwen2.5-coder:7b"

        # 2. RESEARCHER — reasoning-strong models preferred
        elif role == "researcher":
            if has_deepseek:
                return "deepseek", "deepseek-reasoner"
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-latest"
            if has_openai:
                return "openai", "o1"
            if has_gemini:
                return "gemini", "gemini-2.5-pro"
            if has_openrouter:
                keywords = ("reasoning", "thinking", "trinity", "deepseek-r1")
                for m in working_models:
                    if any(x in m.lower() for x in keywords):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"

        # 3. WRITER / EDITOR — fluent prose tier
        elif role in ("writer", "editor"):
            if has_anthropic:
                return "anthropic", "claude-3-5-sonnet-latest"
            if has_openai:
                return "openai", "gpt-4o-mini"
            if has_deepseek:
                return "deepseek", "deepseek-chat"
            if has_gemini:
                return "gemini", "gemini-1.5-flash"
            if has_openrouter:
                keywords = ("llama", "gemma", "mistral")
                for m in working_models:
                    if any(x in m.lower() for x in keywords):
                        return "openrouter", m
                if working_models:
                    return "openrouter", working_models[0]
            return "lokal", "llama3"

        # 4. SOUL — conversational, warm
        elif role == "soul":
            if has_deepseek:
                return "deepseek", "deepseek-chat"
            if has_gemini:
                return "gemini", "gemini-1.5-flash"
            if has_openai:
                return "openai", "gpt-4o-mini"
            if has_openrouter:
                keywords = ("llama", "gemma", "liquid")
                for m in working_models:
                    if any(x in m.lower() for x in keywords):
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

        # Premium tier (s4) — role-tuned: reasoning-strong models for coding/research/security
        if role_lower in ("coder", "researcher", "security"):
            s4 = [
                ("anthropic", "claude-3-5-sonnet-latest"),
                ("deepseek", "deepseek-reasoner"),
                ("openai", "o1"),
                ("gemini", "gemini-2.5-pro"),
            ]
        else:
            s4 = [
                ("anthropic", "claude-3-5-sonnet-latest"),
                ("openai", "gpt-4o"),
                ("gemini", "gemini-2.0-flash"),
                ("deepseek", "deepseek-chat"),
            ]

        s3 = [
            ("deepseek", "deepseek-chat"),
            ("gemini", "gemini-1.5-flash"),
            ("openrouter", or_model),
            ("openai", "gpt-4o-mini"),
            ("mistral", "mistral-large-latest"),
        ]
        s2 = [
            ("openrouter", or_model),
            ("deepseek", "deepseek-chat"),
        ]
        # Local Ollama tier — always-on safety net.
        s1 = [
            ("lokal", "qwen2.5-coder:7b"),
            ("lokal", "llama3"),
            ("lokal", "mistral"),
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

            if conf.get("_source") == "routing.txt":
                explanation = f"{explanation} (via routing.txt)"

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
                "actionable": actionable,
                "source": conf.get("_source", "db")
            })
            
        return insights
