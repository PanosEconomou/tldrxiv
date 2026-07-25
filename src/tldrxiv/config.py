# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Reading the config        #
# ------------------------- #

import os
import tomllib
from pathlib import Path

DEFAULTS = {
    "arxiv"     : {
        "feeds"     : ["hep-th"],
        "types"     : ["new", "cross"],
        "timeout"   : 60,
        },

    "storage"   : {
        "daily_arxiv"   : 1,
        "daily_digest"  : 60,
        },

    "llm"       : {
        "api_key"       : os.environ.get("TLDRXIV_LLM_KEY", ""),
        "temperature"   : 0.3,
        "url"           : "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent",
        },

    "research"  : {
        "work"      : "Generalized symmetry in particular through the lens of 2D CFTs. Interest in Conformal Defects and boundaries as a probe for studying RG flows as well as the mathematical structure of generalized symmetry.",
        "interests" : "Generalized Symmetry as a method for understanding both the mathematical structure of QFT as well as obtaining new kinematical results in specific contenxts. Also some interest in lattices and condensed matter applications of generalized symmetry. Always on the lookout for where generalized symmetry ideas but not necessarily techniques or formalism can be applied in novel areas."
        },
}

def _update(base:dict, update:dict) -> dict:
    output = dict(base)

    for key, value in update.items():
        if isinstance(key, dict) and isinstance(output.get(key), dict):
            output[key] = _update(output[key], value)
        else: output[key] = value
    return output

def _find_config_path(cli_path: Path | None) -> Path | None:
    if cli_path is not None: 
        if cli_path.is_file(): 
            return cli_path
    return None

def _parse_config_file(cfg:dict, path:Path) -> dict:
    try:
        with open(path, "rb") as file:
            local_cfg = tomllib.load(file)
        cfg = _update(cfg, local_cfg)
    except tomllib.TOMLDecodeError as error:
        print(f"Failed to parse config file {path}. Using Default config.")
        print(error)
    except OSError as error:
        print(f"Cannot read config file {path}. Using Default config.")
    return cfg

def load(cli:dict = { "config_file" : Path("") }) -> dict:
    """
    Parses the config file and overrides any arguments from the cli
    """

    cfg     = DEFAULTS.copy()
    path    = _find_config_path(cli["config_file"])
    if path is not None: cfg = _parse_config_file(cfg, path)
    if "config" in cli:
        cfg = _update(cfg, cli["config"])

    return cfg
