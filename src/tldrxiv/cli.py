# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Command Line Interface    #
# ------------------------- #

import os
import sys
import argparse
import shutil
from subprocess import call 
from datetime   import date, timedelta
from argparse   import ArgumentParser, ArgumentTypeError
from pathlib    import Path
from shlex      import split
from pprint     import pprint

from . import feed, paths, config, llm, render

_LOGO = """
 ┓ ┓  ┏┓┏┓•  
╋┃┏┫┏┓ ┃┃ ┓┓┏
┗┗┗┻┛ ┗┛┗┛┗┗┛
"""

_DATE_KEYWORDS = {
    "t"         : 0,
    "today"     : 0, 
    "yesterday" : 1,
}

def _day(text: str) -> date:
    stripped = text.strip().lower()
    if stripped in _DATE_KEYWORDS:
        return date.today() - timedelta(days=_DATE_KEYWORDS[stripped])

    if stripped == len(stripped) * "y":
        return date.today() - timedelta(days=len(stripped))

    if stripped.startswith("-") and stripped[1:].isdigit():
        return date.today() - timedelta(days=int(stripped[1:]))

    try:
        return date.fromisoformat(stripped)

    except ValueError:
        raise ArgumentTypeError(f"{text!r} is not a date. Use 'today', 'yesterday', '-N' for N days ago, or an ISO date like {date.today().isoformat()}")


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog                = "tldrxiv",
        description         = "Digest today's arxiv feed based on your interests!",
        epilog              = "Thanks for using %(prog)s! :>",
    )

    parser.add_argument("date",
                        nargs="?",
                        type=_day,
                        default=date.today(),
                        metavar="DATE",
                        help="Which day's digest: today, yesterday, -N, or YYYY-MM-DD"
                        )

    arxiv       = parser.add_argument_group("arXiv settings")
    arxiv.add_argument("-F", "--feeds", 
                       type=str, 
                       nargs="+", 
                       dest="feeds",
                       default=argparse.SUPPRESS,
                       metavar="FEEDS",
                       help="A list of arXiv feeds you want to analyze"
                       )
    arxiv.add_argument("-t", "--types", "--article-types", 
                       type=str, 
                       dest="types",
                       nargs="+", 
                       default=argparse.SUPPRESS,
                       metavar="TYPES",
                       help="A list of article types you want to filter (e.g. new cross ...)"
                       )
    arxiv.add_argument("-s", "--timeout", 
                       type=int, 
                       dest="timeout",
                       default=argparse.SUPPRESS,
                       metavar="#",
                       help="How long should you wait for a response from arxiv in seconds"
                       )

    system      = parser.add_argument_group("settings")
    system.add_argument("-A", "--daily-arxiv", "--daily-arxiv-store", 
                        type=int, 
                        dest="daily_arxiv",
                        default=argparse.SUPPRESS,
                        metavar="#",
                        help="Maximum number of arxiv feeds to store in cache"
                        ) 
    system.add_argument("-D", "--daily-digest", "--daily-digest-store", 
                        type=int, 
                        dest="daily_digest",
                        default=argparse.SUPPRESS,
                        metavar="#",
                        help=f"Maximum number of daily digests to store in {paths.data_dir()}"
                        ) 
    system.add_argument("-c", "--config", "--config-file", 
                        type=Path, 
                        dest="config",
                        default=paths.config_file(),
                        metavar="/path/to/config.toml",
                        help=f"Override the default config file located in {paths.config_file()}"
                        )
    system.add_argument("-f", "--force", 
                        action="store_true",
                        dest="force",
                        help="Force a fresh download of the arxiv feed and llm digest"
                        )
    system.add_argument("-V", "--verbose", 
                        action="store_true",
                        dest="verbose",
                        help="Print out some additional debug info"
                        )
    system.add_argument("-n", "--no-logo", 
                        action="store_false",
                        dest="logo",
                        help="Skip showing the logo in the output"
                        )
    system.add_argument("-o", "--output", 
                        type=Path,
                        dest="output",
                        metavar="FILE",
                        help="Specify an extra file to save the output instead of printing it."
                        )

    llm         = parser.add_argument_group("llm settings")
    llm.add_argument("-k", "--key", "--api-key", 
                     type=str, 
                     dest="key",
                     default=argparse.SUPPRESS,
                     metavar="AC...",
                     help="Your LLM API Key (for Gemini go to: aistudio.google.com)"
                     )
    llm.add_argument("-u", "--url", 
                     type=str, 
                     dest="url",
                     default=argparse.SUPPRESS,
                     metavar="http://llm.api.com/",
                     help="LLM API URL"
                     )
    llm.add_argument("-K", "--temperature", 
                     type=float, 
                     dest="temperature",
                     default=argparse.SUPPRESS,
                     metavar="TEMP",
                     help="Temperature of model"
                     )

    research    = parser.add_argument_group("your research interests")
    research.add_argument("-w", "--work", 
                          type=str, 
                          dest="work",
                          default=argparse.SUPPRESS,
                          metavar="X",
                          help="What are you currently working on?"
                          )
    research.add_argument("-i", "--interests", 
                          type=str, 
                          dest="interests",
                          default=argparse.SUPPRESS,
                          metavar="X",
                          help="What are your general research interests?"
                          )

    return parser


_MAP = {
    "feeds":        ("arxiv",    "feeds"),
    "types":        ("arxiv",    "types"),
    "timeout":      ("arxiv",    "timeout"),
    "daily_arxiv":  ("storage",  "daily_arxiv"),
    "daily_digest": ("storage",  "daily_digest"),
    "api_key":      ("llm",      "api_key"),
    "url":          ("llm",      "url"),
    "temperature":  ("llm",      "temperature"),
    "work":         ("research", "work"),
    "interests":    ("research", "interests"),
}

def _cli_overrides(args) -> dict:
    overrides = {}
    for dest, value in vars(args).items():
        if dest in _MAP:
            table, key = _MAP[dest]
            overrides.setdefault(table, {})[key] = value

    return overrides

def _parse_args(argv) -> dict:
    args = _build_parser().parse_args(argv)

    cli = {
        "force": args.force,
        "verbose": args.verbose,
        "date": args.date,
        "logo": args.logo,
        "config_file": args.config,
        "config": _cli_overrides(args)
    }

    if args.output is not None:
        cli["output"] = args.output

    return cli

def _write_output(cli:dict, answer:dict) -> None:
    output_str = ((_LOGO + "\n") if cli["logo"] else "") + answer["formatted"]
    if "output" in cli:
        try:
            cli["output"].parent.mkdir(parents = True, exist_ok = True)
            cli["output"].write_text(output_str)
        except OSError as error:
            raise RuntimeError(f"Unable to write to {cli["output"]} - {error.strerror}") from error
    else:
        print(output_str)

def _build_config_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog                = "tldrxiv config",
        description         = f"Configure tildrxiv. This opens the file in {paths.config_file()} with your default editor",
        epilog              = "Thanks for using %(prog)s! :>",
    )

    parser.add_argument("-c", "-f", "--form", "--file",
                        type=Path, 
                        dest="file",
                        metavar="/path/to/config.toml",
                        help=f"Override the default config file located in {paths.config_file()} using the contents of /path/to/config.toml"
                        )

    parser.add_argument("-d", "--default", "--default-force",
                        action="store_true",
                        dest="default",
                        help=f"Override config file located in {paths.config_file()} with the default config"
                        )
    return parser

def _get_editor_cmd() -> list | None:
    for var in ["VISUAL", "EDITOR"]:
        val = os.environ.get(var)
        if val:
            return split(val)
    
    for program in ["nvim", "vim", "nano", "vi", "textedit"]:
        if shutil.which(program):
            return [program]

    return None

def _configure(args) -> int:
    filepath = paths.ensure_parent(paths.config_file())
    if args.file is not None and not args.default:
        try:
            shutil.copy(args.file, filepath)
        except OSError as error:
            raise RuntimeError(f"Unable to copy {args.file} to {filepath}- {error.strerror}") from error

    if args.default or not filepath.is_file():
        try:
            shutil.copy(paths.default_config_file(), filepath)
        except OSError as error:
            raise RuntimeError(f"Unable to copy {paths.default_config_file()} to {filepath}- {error.strerror}") from error
        
    cmd = _get_editor_cmd()
    if cmd is None:
        print(f"[ERROR] There is no default editor. Set $EDITOR, or edit {filepath} directly.", file = sys.stderr)
        return 1

    editor = call([*cmd, str(filepath)])
    if editor != 0:
        print(f"[WARNING] Editor exited with status: {editor}.", file = sys.stderr)

    cfg = config.load({"config_file" : paths.config_file()})
    if cfg["default"]:
        print(f"[WARNING] There was a problem setting your config and you are using the default! Please run tldrxiv config or edit {filepath} directly", file=sys.stderr)
        return 1

    print("tldrXiv configured successfully!")
    return 0

def main(argv: list[str] | None = None) -> int:

    if sys.argv is not None and len(sys.argv) >= 2 and sys.argv[1] == "config":
        args = _build_config_parser().parse_args(sys.argv[2:])
        return _configure(args)

    cli = _parse_args(argv)
    cfg = config.load(cli)
    if cfg["default"]:
        print(f"[WARNING] You are using a default config! Please run tldrxiv config to set your research interests!", file=sys.stderr)

    if cli["date"] == date.today():
        feed.download(cfg["arxiv"]["feeds"], force=cli["force"], timeout=cfg["arxiv"]["timeout"])
    papers = feed.parse(paths.feed_file(cli["date"].isoformat()), types=cfg["arxiv"]["types"])
    feed.cleanup(cfg["storage"]["daily_arxiv"])

    answer = render.parse_digest(cli["date"].isoformat())
    if answer is None or cli["force"]:
        payload = llm.request_digest(cfg["llm"]["url"], cfg["llm"]["api_key"], papers, cfg["research"]["work"], cfg["research"]["interests"], cfg["llm"]["temperature"])
        answer = render.extract_answer(payload,papers)
        render.save_digest(answer, cli["date"].isoformat())

    render.cleanup(cfg["storage"]["daily_digest"])
    if cli["verbose"]:
        pprint(cli)
        pprint(cfg)
    _write_output(cli, answer)

    return 0
