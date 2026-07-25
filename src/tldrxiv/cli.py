# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Command Line Interface    #
# ------------------------- #

import argparse
from datetime import date, timedelta
from argparse import ArgumentParser, ArgumentTypeError
from pathlib  import Path

from . import feed, paths, config, llm, render

_LOGO = """
 ┓ ┓  ┏┓┏┓•  
╋┃┏┫┏┓ ┃┃ ┓┓┏
┗┗┗┻┛ ┗┛┗┛┗┗┛
"""

_DATE_KEYWORDS = {
    "today"     : 0, 
    "t"         : 0,
    "yesterday" : 1,
    "y"         : 1,
    "yy"        : 2,
    "yyy"       : 3,
}

def _day(text: str) -> date:
    stripped = text.strip().lower()
    if stripped in _DATE_KEYWORDS:
        return date.today() - timedelta(days=_DATE_KEYWORDS[stripped])

    if stripped.startswith("-") and stripped[1:].isdigit():
        return date.today() - timedelta(days=int(stripped[1:]))

    try:
        return date.fromisoformat(stripped)

    except ValueError:
        raise ArgumentTypeError(f"{text!r} is not a date. Use 'today', 'yesterday', '-N' for N days ago, or an ISO date like {date.today().isoformat()}")


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog        = "tldrxiv",
        description = "Digest today's arxiv feed based on your interests!",
        epilog      = "Thanks for using %(prog)s! :>"
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

    system      = parser.add_argument_group("storage settings")
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

    system.add_argument("-n", "--no-logo", 
                        action="store_false",
                        dest="logo",
                        help="Skip showing the logo in the output"
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
        "date": args.date,
        "logo": args.logo,
        "config_file": args.config,
        "config": _cli_overrides(args)
    }

    return cli

def main(argv: list[str] | None = None) -> int:

    cli = _parse_args(argv)
    cfg = config.load(cli)

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

    if cli["logo"]: print(_LOGO)
    print(answer["formatted"]) 
    return 0
