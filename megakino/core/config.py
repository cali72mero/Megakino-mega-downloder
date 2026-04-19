import json
from dataclasses import asdict, dataclass
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
            return
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
            known_fields = AppConfig.__dataclass_fields__.keys()
            filtered = {key: value for key, value in data.items() if key in known_fields}
            self.config = AppConfig(**filtered)
        except (OSError, TypeError, json.JSONDecodeError):
            self.config = AppConfig()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = CONFIG_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.config), f, indent=4)
            f.write("\n")
        temp_file.replace(CONFIG_FILE)


config_manager = ConfigManager()
config = config_manager.config
