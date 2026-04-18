import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from appdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("megakino", "Tmaster055"))
CONFIG_FILE = CONFIG_DIR / "config.json"

@dataclass
class AppConfig:
    download_path: str = str(Path.home() / "Downloads" / "Megakino")
    concurrent_downloads: int = 4
    preferred_provider: str = "Megakino"
    theme: str = "default"
    show_animations: bool = False

class ConfigManager:
    def __init__(self):
        self.config = AppConfig()
        self.load()

    def load(self):
        if not CONFIG_FILE.exists():
            self.save()
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.config = AppConfig(**data)
        except Exception:
            pass # fallback to default if parsing fails

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self.config), f, indent=4)

config_manager = ConfigManager()
config = config_manager.config
