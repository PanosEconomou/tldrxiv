import os
import json
from datetime import date
from pathlib import Path
from re import split, compile
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from xml.etree.ElementTree import fromstring as xml_file

API_KEY     = os.environ["LLM_KEY"]
URL         = os.environ["LLM_URL"]
FEED        = os.environ["ARXIV_OUTPUT"]
DIGEST_DIR  = Path(os.environ["DIGEST_DIR"])
WORK        = os.environ["RESEARCH_WORK"]
INTERESTS   = os.environ["RESEARCH_INTERESTS"]
SYSTEM      = f"""
You triage the daily arXiv announcement for a PhD student.

Their work: {WORK}

Standing interests: {INTERESTS}

They can read titles themselves. What they want from you is what the batch reveals: what problems people are choosing to work on, how they frame them, what they take for granted, and where papers pull against each other.

Ground every claim in the abstracts you were given. You may describe what an abstract assumes, what it positions itself against, and the gap between what it claims and what it demonstrates. You may NOT assert citation relationships, influence, or lineage between papers or to prior work — you cannot see references, and a plausible guess is worse than silence here.

Most days are unremarkable. When a day is unremarkable, say so briefly and stop. Do not manufacture a theme. Do not use the same organizing move two days running.
"""
INSTRUCTION = """
The papers announced today are numbered below.

Write one or two paragraphs — digest, no headers, no bullets. Refer to
specific papers by their number in square brackets, like [7], only where
a specific paper carries the point.

Then, separately, list the papers worth actually opening today. Judge
against the interests above, not against general interestingness. If
that list is empty, leave it empty; a short honest answer beats a padded
one.

Return JSON: {"digest": "...", "worth_opening": [{"id": 7, "why": "one
sentence"}]}
"""
SCHEMAS     = {
    "atom" : "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}


with open(FEED, 'r') as file:
    atom_feed   = xml_file(file.read())
    entries = atom_feed.findall("atom:entry", SCHEMAS)
    papers = [{
        "arxiv_id"  : entry.findtext("atom:id", "", SCHEMAS).replace("oai:arXiv.org:", ""),
        "title"     : entry.findtext("atom:title", "", SCHEMAS),
        "summary"   : split(r"Abstract:\s*", entry.findtext("atom:summary", "", SCHEMAS), maxsplit=1)[-1]
    } for entry in entries ]

LISTING     = "\n\n".join([f"[{i}] {paper['title']}\n{paper['summary']}" for i, paper in enumerate(papers,1)])

PROMPT      = INSTRUCTION + f"\n\n{len(papers)} papers were announced today:\n\n" + LISTING


body    = {
    "systemInstruction": {
        "parts": [{
            "text": SYSTEM
        }]
    },
    "contents": [{
        "role": "user",
        "parts": [{
            "text": PROMPT
        }]
    }],
    "generationConfig": {
        "temperature": 0.3,
        "responseMimeType": "application/json"
    }
}

req = Request(
    URL,
    data = json.dumps(body).encode("utf-8"),
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    },
    method = "POST"
)

try: 
    with urlopen(req, timeout=60) as response:
        payload = json.load(response)
except HTTPError as e:
    print(f"HTTP {e.code}")
    print(e.read().decode("utf-8","replace"))
    raise

def linkify(text, papers): 
    misses = []
    PATTERN = compile(r"\[(\d+)\]")

    def resolve(match):
        idx = int(match.group(1))
        if 1 <= idx <= len(papers):
            p = papers[idx - 1]
            return f"[{p['arxiv_id']}](https://arxiv.org/abs/{p['arxiv_id']})"
        misses.append(idx)
        return match.group(0)

    result = PATTERN.sub(resolve, text)
    if misses:
        print(f"warning: model referenced out-of-range indices {misses}", file=__import__("sys").stderr)
    return result

def listify(dictionary, papers):
    if len(dictionary) == 0: return ""
    return " - " + " - ".join([ f"[{papers[paper["id"]-1]["arxiv_id"]}](https://arxiv.org/abs/{papers[paper["id"] - 1]["arxiv_id"]}) {paper["why"]}\n" for paper in dictionary])

answer              = json.loads(payload["candidates"][0]['content']['parts'][0]['text'])
answer["digest"]    = linkify(answer["digest"], papers)
answer['formatted'] = "\n\n".join([answer["digest"], listify(answer["worth_opening"], papers)])

output = DIGEST_DIR / f"{str(date.today())}.json"
output.parent.mkdir(parents = True, exist_ok = True)
with open(output, "w", encoding="utf-8") as file :
    json.dump(answer, file, ensure_ascii=False)
