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
from sys     import stderr

DEFAULTS = {
    "default": True,
    "arxiv"     : {
        "feeds"     : ["hep-th"],
        "types"     : ["new", "cross"],
        "timeout"   : 60,
        },

    "storage"   : {
        "daily_arxiv"   : 5,
        "daily_digest"  : 60,
        },

    "llm"       : {
        "api_key"       : "",
        "temperature"   : 0.5,
        "url"           : "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent",
        },

    "research"  : {
        "work"      : "This is the default config, so the user hasn't entered any info. Pleasegive them a general summary instead and clearly begin your prompt suggesting that they run `tldrxiv config` to set their research interests so that you provide a more tailored summary.",
        "interests" : "This is the default config, so the user hasn't entered any info. Pleasegive them a general summary instead and clearly begin your prompt suggesting that they run `tldrxiv config` to set their research interests so that you provide a more tailored summary."        },
}

def _update(base:dict, update:dict) -> dict:
    output = dict(base)

    for key, value in update.items():
        if isinstance(value, dict) and isinstance(output.get(key), dict):
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
        cfg["default"] = False
    except tomllib.TOMLDecodeError as error:
        print(f"Failed to parse config file {path}. Using Default config.", file=stderr)
        print(error, file=stderr)
        cfg["default"] = True
    except OSError as error:
        print(f"Cannot read config file {path}. Using Default config.", file=stderr)
        cfg["default"] = True
    return cfg

def _resolve_api_key(text:str) -> str:
    if text.startswith("$"):
        var = os.environ.get(text[1:])
        if var is not None:
            return var
        else:
            raise SystemExit(f"config: api_key refers to {text}, which is not set.\nDo tldrxiv config to set api_key or set {text} in your environment.")
    if text == "":
        var = os.environ.get("TLDRXIV_LLM_KEY")
        if var is not None:
            return var
        else:
            raise SystemExit(f"config: api_key was blank or unset, so I looked for $TLDRXIV_LLM_KEY, which was not set.\nDo tldrxiv config to set api_key or set $TLDRXIV_LLM_KEY in your environment.")
    return text


def load(cli:dict = { "config_file" : Path("") }) -> dict:
    """
    Parses the config file and overrides any arguments from the cli
    """

    cfg     = DEFAULTS.copy()
    path    = _find_config_path(cli["config_file"])
    if path is not None: 
        cfg = _parse_config_file(cfg, path)

    if "config" in cli:
        cfg = _update(cfg, cli["config"])
        cfg["default"] = cfg["default"] or cli["config"] != {}
    
    cfg["llm"]["api_key"] = _resolve_api_key(cfg["llm"]["api_key"])

    return cfg
