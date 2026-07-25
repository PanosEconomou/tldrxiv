# ------------------------- #
#  ┓ ┓  ┏┓┏┓•               #
# ╋┃┏┫┏┓ ┃┃ ┓┓┏             #
# ┗┗┗┻┛ ┗┛┗┛┗┗┛             #
#                           # 
# Download arxiv feed       #
# ------------------------- #

from sys                    import exit
from pathlib                import Path
from datetime               import date
from urllib.request         import Request, urlopen
from urllib.error           import HTTPError, URLError
from gzip                   import decompress
from xml.etree.ElementTree  import fromstring as read_xml, ParseError, parse as read_xml_file
from re                     import split, compile

from .                      import paths

SCHEMAS     = {
    "atom" : "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}
USER_AGENT = "tldrxiv/0.1 (personal arXiv digest, one request per day)"

def _feed_url(feeds:list) -> str:
    return "https://rss.arxiv.org/atom/" + "+".join(feeds)

def _write(raw: bytes, path:Path) -> Path:
    path.write_bytes(raw)
    return path

def download(feeds:list, force:bool = False, timeout:int = 60) -> Path:
    """
    Download today's feed
    """
    day     = date.today().isoformat()
    file    = paths.ensure_parent(paths.feed_file(day))
    
    if file.is_file() and not force:
        return file

    request = Request(
        url = _feed_url(feeds),
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip"
        }
    )

    try: 
        with urlopen(request, timeout = timeout) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = decompress(raw)

    except HTTPError as error:
        print(f"arXiv returned Error {error.code}")
        print(error.read().decode("utf-8", "replace"))
        exit("Failed to pull from arXiv")

    except URLError as error:
        print(f"Attempted to reach arXiv but got {error.reason}")
        exit("Failed to reach arXiv")
    
    try: 
        root = read_xml(raw)

    except ParseError as error:
        exit(f"{_feed_url(feeds)} did not return a valid XML")

    if root.tag != "{http://www.w3.org/2005/Atom}feed": 
        exit(f"{_feed_url(feeds)} did returned a malformed XML")
        
    return _write(raw, file)

def parse(path:Path, types:list[str] = []) -> list[dict]:
    """
    Read a stored file into a collection of papers
    """

    try:
        root = read_xml_file(path).getroot()

    except ParseError as error:
        print(error)
        exit(f"{path} did not return a valid XML")

    except OSError as error:
        print(error)
        exit(f"Cannot read file {path}.")

    wanted = {type for type in types}
    papers = []

    for entry in root.findall("atom:entry", SCHEMAS):
        summary_raw = entry.findtext("atom:summary", "", SCHEMAS) or ""
        kind        = entry.findtext("arxiv:announce_type", "", SCHEMAS) or ""
        if wanted and kind not in wanted:
            continue
        
        papers.append({
            "arxiv_id"  : entry.findtext("atom:id", "", SCHEMAS).replace("oai:arXiv.org:", ""),
            "title"     : entry.findtext("atom:title", "", SCHEMAS),
            "summary"  : split(r"Abstract:\s*", summary_raw, maxsplit = 1)[-1]
        })
    return papers

def cleanup(max_entries:int) -> None:
    """
    Given a max_entries it cleans up older arxiv saves to keep max_entries recent ones.
    """

    if max_entries <= 0:
        raise ValueError(f"max_entries must be > 0 for feed. Current is {max_entries}")
    if not paths.cache_dir().is_dir(): 
        return
    if len([path for path in paths.cache_dir().iterdir() if path.is_file()]) <= max_entries:
        return

    pattern = compile(r"^feed-(\d{4}-\d{2}-\d{2})\.xml$")
    cached_feeds = []
    for path in paths.cache_dir().iterdir():
        date = pattern.match(path.name)
        if date:
            cached_feeds.append((date.group(1), path))
    cached_feeds.sort(reverse=True)

    for _, path in cached_feeds[max_entries:]:
        path.unlink(missing_ok = True)


