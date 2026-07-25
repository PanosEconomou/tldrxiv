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
from xml.etree.ElementTree  import fromstring as read_xml, ParseError

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
