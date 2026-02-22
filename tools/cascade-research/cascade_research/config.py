from pathlib import Path
import yaml
import os


DEFAULT_CONFIG = {
    "project_root": str(Path.home() / "Desktop/moltathon/cascade"),
    "directories": [
        {"path": "product-research", "doc_type": "research"},
        {"path": "data/product-research", "doc_type": "research"},
        {"path": "outputs", "doc_type": "synthesis", "exclude": ["cascade-pitch-deck"]},
        {"path": "data", "doc_type": "planning", "include_only_md": True, "exclude": ["product-research"]},
    ],
    "chunking": {
        "max_chunk_size": 800,
        "chunk_overlap": 100,
    },
    "storage": {
        "path": str(Path.home() / ".cascade-research"),
        "collection_name": "cascade-research",
    },
    "query": {
        "top_k": 5,
    },
}


def _find_config():
    """Find config.yaml relative to this package."""
    return Path(__file__).parent.parent / "config.yaml"


def load_config():
    config_file = _find_config()
    if config_file.exists():
        with open(config_file) as f:
            user_config = yaml.safe_load(f) or {}
        # Deep merge with defaults, then add any extra keys from user config
        config = {}
        for key, default_val in DEFAULT_CONFIG.items():
            if isinstance(default_val, dict):
                config[key] = {**default_val, **user_config.get(key, {})}
            else:
                config[key] = user_config.get(key, default_val)
        # Carry over keys that exist in user config but not in defaults
        for key in user_config:
            if key not in config:
                config[key] = user_config[key]
        return config
    return DEFAULT_CONFIG.copy()


def get_project_root():
    return Path(load_config()["project_root"])


def get_storage_path():
    raw = load_config()["storage"]["path"]
    return Path(os.path.expanduser(raw))


def get_collection_name():
    return load_config()["storage"]["collection_name"]


def get_directories():
    return load_config()["directories"]


def get_chunking():
    return load_config()["chunking"]


def get_query_defaults():
    return load_config()["query"]
