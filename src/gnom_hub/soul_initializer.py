"""Soul-Initializer: Erstellt Basis-Souls für jeden Agenten."""

def get_base_soul(agent_name: str):
    """Erstellt eine vernünftige Basis-Soul für jeden Agenten."""
    name = agent_name.lower()
    soul = {
        "role": name.replace("ag", "").replace("agent", ""),
        "permissions": ["read"],
        "directive": "Hilf dem Schwarm bei seiner Aufgabe und kommuniziere klar."
    }
    if "general" in name:
        soul["permissions"] += ["@job", "general"]
        soul["directive"] = "Koordiniere Tasks und verteile Arbeit im Schwarm."
    elif "writer" in name:
        soul["permissions"] += ["write"]
        soul["directive"] = "Schreibe Texte, Skripte und kreative Inhalte."
    elif "coder" in name:
        soul["permissions"] += ["write", "run"]
        soul["directive"] = "Programmiere, schreibe Code, setze technisch um."
    elif "crawler" in name:
        soul["permissions"] += ["read", "crawl"]
        soul["directive"] = "Crawle URLs, extrahiere Inhalte, liefere Rohdaten an den Schwarm."
    elif "researcher" in name:
        soul["directive"] = "Recherchiere, sammle Informationen, fasse zusammen."
    elif "editor" in name:
        soul["permissions"] += ["write"]
        soul["directive"] = "Prüfe, überarbeite und finalisiere Ergebnisse."
    elif "summarizer" in name:
        soul["directive"] = "Filtere Fakten, komprimiere Kontext."
    elif "backup" in name:
        soul["permissions"] += ["backup"]
        soul["directive"] = "Sichere den Workspace, erstelle Snapshots."
    elif "skill" in name:
        soul["permissions"] += ["write", "godmode", "run"]
        soul["directive"] = "Führe Befehle aus, deploye, manage Infrastruktur."
    elif "desktop" in name or "vision" in name:
        soul["permissions"] += ["desktop"]
        soul["directive"] = "Steuere den Bildschirm, führe visuelle Aufgaben aus."
    elif "security" in name:
        soul["permissions"] += ["security"]
        soul["directive"] = "Überwache Sicherheit, genehmige gefährliche Aktionen."
    return soul
