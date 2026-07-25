# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Command Line Interface    #
# ------------------------- #

from datetime import date

from . import feed, paths, config, llm, render

EXIT_OK, EXIT_ERROR, EXIT_CONFIG, EXIT_INTERRUPTED = 0, 1, 2, 130

def main(argv: list[str] | None = None) -> int:

    cfg = config.load()

    feed.download(cfg["arxiv"]["feeds"])
    papers = feed.parse(paths.feed_file(date.today().isoformat()), types=cfg["arxiv"]["type"])
    feed.cleanup(cfg["storage"]["daily_arxiv"])

    answer = render.parse_digest(date.today().isoformat())
    
    if answer is None:
        payload = llm.request_digest(cfg["llm"]["url"], cfg["llm"]["api_key"], papers, cfg["research"]["work"], cfg["research"]["interests"])
        
        answer = render.extract_answer(payload,papers)

    print(answer["formatted"])
    
    render.save_digest(answer, date.today().isoformat())
    render.cleanup(cfg["storage"]["daily_digest"])
    return EXIT_OK 
