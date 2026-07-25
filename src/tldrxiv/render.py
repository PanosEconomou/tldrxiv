# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Prettifying and outputing #
# ------------------------- #

from re         import compile
from json       import loads, dumps

from .          import paths

def _linkify(text:str, papers:list[dict]) -> str:
    pattern =  compile(r"\[(\d+)\]")

    def resolve(match):
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(papers):
            return f"[[{papers[idx]['arxiv_id']}](https://arxiv.org/abs/{papers[idx]['arxiv_id']})]"
        return match.group(0)

    return pattern.sub(resolve, text)

def _listify(entries:list[dict], papers:list[dict]) -> str:
    def resolve(entry):
        idx = entry["id"] - 1
        if 0 <= idx < len(papers):
            return f" - [[{papers[idx]["arxiv_id"]}](https://arxiv.org/abs/{papers[idx]['arxiv_id']})] {_linkify(entry['why'], papers)}"
        return f" - [ERROR] {_linkify(entry['why'], papers)}"

    return "\n".join(list(map(resolve, entries)))
    
def _idfy(entries:list[dict], papers:list[dict]) -> list:
    def resolve(entry):
        idx = entry["id"] - 1
        if 0 <= idx < len(entries): entry["id"] = papers[idx]["arxiv_id"]
        else: entry["id"] = "ERROR"

    return list(map(resolve, entries))
        

def extract_answer(payload:dict, papers:list[dict]) -> dict:
    """
    Formats the LLM output into a well understood dictionary ready for export.
    """
    answer                  = loads(payload["candidates"][0]["content"]['parts'][0]['text'])
    answer["digest"]        = _linkify(answer["digest"], papers)
    answer["formatted"]     = "\n\n".join([answer["digest"], _listify(answer["worth_opening"], papers)])
    answer["worth_opening"] = _idfy(answer["worth_opening"], papers)

    return answer

def save_digest(answer:dict, day:str) -> bool:
    """
    Append the digest in the correct directory for the date's arxiv feed.
    Returns True if the new file is nonempty
    """
    output = paths.ensure_parent(paths.digest_file(day))
    return output.write_text(dumps(answer, ensure_ascii = False), encoding = "utf-8") > 0

def cleanup(max_entries:int) -> None:
    """
    Given a max_entries it cleans up older digest saves to keep max_entries recent ones.
    """

    if max_entries <= 0:
        raise ValueError(f"max_entries must be > 0 for digest. Current is {max_entries}")
    if not paths.cache_dir().is_dir(): 
        return
    if len([path for path in paths.cache_dir().iterdir() if path.is_file()]) <= max_entries:
        return

    pattern = compile(r"^(\d{4}-\d{2}-\d{2})\.json$")
    cached_feeds = []
    for path in paths.cache_dir().iterdir():
        date = pattern.match(path.name)
        if date:
            cached_feeds.append((date.group(1), path))
    cached_feeds.sort(reverse=True)

    for _, path in cached_feeds[max_entries:]:
        path.unlink(missing_ok = True)

