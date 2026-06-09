import socket
import ssl
import time
import gzip
from dataclasses import dataclass, field

class URL:

    cache = {}

    def __init__(self, url):
        try:
            scheme, rest = url.split(":", 1)

            if scheme in ["http", "https", "file"]:
                self.scheme = scheme
                url = rest[2:]
            elif scheme in ["data", "about"]:
                self.scheme = scheme
                self.path = rest
                return
            elif scheme == "view-source":
                self.scheme = scheme
                self.inner_scheme, url = rest.split("://", 1)
                scheme = self.inner_scheme
            else:
                raise ValueError(f"Unknown scheme: {scheme}")

            if self.scheme == "file":
                self.path = url
                return 

            if "/" not in url:
                url = url + "/"
            host, url = url.split("/", 1)
            self.headers = {"Host": host}
            self.path = "/" + url

            if scheme == "http":
                self.port = 80
            elif scheme == "https":
                self.port = 443

            if ":" in self.headers["Host"]:
                self.headers["Host"], port= self.headers["Host"].split(":", 1)
                self.port = int(port)

            self.sockets = {}
        except (ValueError, IndexError) as e:
            self.scheme = "about"
            self.path = "blank"


    def request(self):
        return self._request(0)

    def _request(self, redirect_count):
        if redirect_count > 12:
            raise Exception("Too many redirects")

        use_scheme = self.inner_scheme if self.scheme == "view-source" else self.scheme

        if self.scheme == "file":
            with open(self.path, 'r', encoding="utf-8") as file:
                return file.read()

        if self.scheme in ["data", "about"]:
            return self.path

        url_string = self.scheme + "://" + self.headers["Host"] + self.path

        if url_string in self.cache:
            entry = self.cache[url_string]
            cache_control = entry["headers"].get("cache-control", "")
            age = time.time() - entry["timestamp"]
            max_age = int(cache_control.split("max-age=")[-1]) if "max-age=" in cache_control else 0
            if age < max_age:
                return entry["body"].decode("utf-8")

        host = self.headers["Host"]
        if host in self.sockets:
            s, response = self.sockets[host]
        else:
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )

            self.headers |= {"Connection" : "keep-alive"}
            self.headers |= {"User-Agent" : "25Ting following browser.engineering"}
            self.headers |= {"Accept-Encoding" : "gzip"}

            s.connect((self.headers["Host"], self.port))
            if use_scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.headers["Host"])
 
            response = s.makefile("rb", newline="\r\n")

        request = "GET {} HTTP/1.1\r\n".format(self.path)
        for name, value in self.headers.items():
            request += "{}: {}\r\n".format(name, value)
        request += "\r\n"
        s.send(request.encode("utf8"))

        statusline = response.readline()
        version, status, explanation = statusline.decode("utf-8").split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf-8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        if status.startswith("3"):
            location = response_headers["location"]
            if location.startswith("/"):
                location = self.scheme + "://" + host + location
            return URL(location)._request(redirect_count + 1)

        if "transfer-encoding" in response_headers and response_headers["transfer-encoding"] == "chunked":
            content = b""
            while True:
                size_line = response.readline()
                chunk_size = int(size_line.strip(), 16)
                if chunk_size == 0:
                    break
                content += response.read(chunk_size)
                response.read(2)
        elif "content-length" in response_headers:
            content = response.read(int(response_headers["content-length"]))
        else:
            content = response.read()
        
        if response_headers.get("content-encoding") == "gzip":
            content = gzip.decompress(content)

        self.sockets[host] = (s, response)

        cache_control = response_headers.get("cache-control", "")
        if status == "200" and "no-store" not in cache_control:
            if "max-age=" in cache_control or cache_control == "":
                self.cache[url_string] = {
                    "body": content,
                    "headers": response_headers,
                    "timestamp": time.time()
                }

        return content.decode("utf-8")

@dataclass
class Text:
    text: str
    parent: 'Text' = None
    children: list = field(default_factory=list)

    def __repr__(self):
        return repr(self.text)

@dataclass
class Element:
    tag: str
    attributes: dict[str, str]
    parent: 'Element' = None
    children: list = field(default_factory=list)

    def __repr__(self):
        return "<" + self.tag + ">"


entity_map = {
    '&lt;' : '<',
    '&rt;' : '>',
    '&gt;' : '>',
    '&quot;' : '"',
    '&#39;' : '\'',
}

def source(body):
    out = []

    out.append(Text(body))

    return out


class HTMLParser:

    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def get_attributes(self, text):
        parts = text.split()
        tags = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value

            else:
                attributes[attrpair.casefold()] = ""
        return tags, attributes

    def parse(self):
        text = ""
        i = 0
        in_tag = False
        while i < len(self.body):
            c = self.body[i]
            if c == '<':
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            elif in_tag:
                text += c
            elif not in_tag:
                if c == '&':
                    end = self.body.find(';', i)
                    if end != -1:
                        entity = self.body[i:end+1]
                        text += entity_map.get(entity, entity,)
                        i = end + 1
                        continue
                text += c
            i += 1
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

    def add_text(self, text):
        if text.isspace(): return

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return

        if tag.startswith("/"):
            if len(self.unfinished) == 1: return 
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        import os
        default_path = os.path.abspath("debug.txt")
        url_string = f"file://{default_path}"
        load(URL(url_string))
        sys.exit()

    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)

