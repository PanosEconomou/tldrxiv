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

def _linkify(text:str, papers:list) -> str:
    pattern =  compile(r"\[(\d+)\]")

    def resolve(match):
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(papers):
            return f"[[{papers[idx]['arxiv_id']}](https://arxiv.org/abs/{papers[idx]['arxiv_id']})]"
        return match.group(0)

    return pattern.sub(resolve, text)

def _listify(entries:list, papers:list) -> str:
    def resolve(entry):
        idx = entry["id"] - 1
        if 0 <= idx < len(papers):
            return f" - [[{papers[idx]["arxiv_id"]}](https://arxiv.org/abs/{papers[idx]['arxiv_id']})] {_linkify(entry['why'], papers)}"
        return f" - [ERROR] {_linkify(entry['why'], papers)}"

    return "\n".join(list(map(resolve, entries)))
    
def _idfy(entries:list, papers:list) -> list:
    def resolve(entry):
        idx = entry["id"] - 1
        if 0 <= idx < len(entries): entry["id"] = papers[idx]["arxiv_id"]
        else: entry["id"] = "ERROR"

    return list(map(resolve, entries))
        

def extract_answer(payload:dict, papers:list) -> dict:
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

