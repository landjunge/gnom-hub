from ...core.config import Config
from gnom_hub.db.schema import init_database

class AdminService:
    def nuke(self):
        Config.DB_PATH.unlink(missing_ok=True)
        init_database()

    def clean(self):
        for p in Config.LOG_DIR.glob("**/*"):
            if p.is_file():
                p.unlink(missing_ok=True)
