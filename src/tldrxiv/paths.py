# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Path resolution           #
# ------------------------- #

import os
from pathlib                import Path

NAME = "tldrxiv"

def _base(env_var:str, fallback:str) -> Path:
    raw     = os.environ.get(env_var, "")
    root    = Path(raw) if raw.startswith("/") else Path.home() / fallback
    return root / NAME

# ------------------------- #
# MAIN DIRECTORIES          # 
# ------------------------- #

def config_dir() -> Path:
    """
    default: ~/.config/tldrxiv
    """
    return _base("XDG_CONFIG_HOME", ".config")

def cache_dir() -> Path:
    """
    default: ~/.cache/tldrxiv
    """
    return _base("XDG_CACHE_HOME", ".cache")

def data_dir() -> Path:
    """
    default: ~/.local/share/tldrxiv/digests
    """
    return _base("XDG_DATA_HOME", ".local/share") / "digests"

def source_dir() -> Path:
    return Path(__file__).parent

# ------------------------- #
# SPECIFIC FILES            # 
# ------------------------- #

def config_file() -> Path: 
    return config_dir() / "config.toml"

def default_config_file() -> Path: 
    return source_dir() / "data" / "config.toml"

def feed_file(day:str) -> Path:
    return cache_dir() / f"feed-{day}.xml"

def digest_file(day:str) -> Path:
    return data_dir() / f"{day}.json"

# ------------------------- #
# DEBUG FEATURES            # 
# ------------------------- #

def ensure_parent(path:Path) -> Path:
    path.parent.mkdir(parents = True, exist_ok = True)
    return path

# Debug via python -m tldrxiv.paths
if __name__ == "__main__": 
    from datetime import date
    today = date.today().isoformat()
    for name, value in [
        ("config",  config_file()),
        ("feed",    feed_file(today)),
        ("digest",  digest_file(today)),
    ]:
        print(f"{name:>15}| {value}")

