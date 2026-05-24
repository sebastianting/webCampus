import socket
import ssl
import time
import gzip

class URL:

    cache = {}

    def __init__(self, url):
        scheme, rest = url.split(":", 1)

        if scheme in ["http", "https", "file"]:
            self.scheme = scheme
            url = rest[2:]
        elif scheme in ["data"]:
            self.scheme = scheme
            url = rest
        elif scheme == "view-source":
            self.scheme = scheme
            self.inner_scheme, url = rest.split("://", 1)
            scheme = self.inner_scheme
        else:
            raise ValueError(f"Unknown scheme: {scheme}")

        if self.scheme == "file":
            self.path = url
            return 

        if self.scheme == "data":
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


    def request(self):
        return self._request(0)

    def _request(self, redirect_count):
        if redirect_count > 12:
            raise Exception("Too many redirects")
        
        use_scheme = self.inner_scheme if self.scheme == "view-source" else self.scheme
        
        if self.scheme == "file":
            with open(self.path, 'r', encoding="utf-8") as file:
                return file.read()
        
        if self.scheme == "data":
            return self.body

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

entity_map = {
    '&lt;' : '<',
    '&rt;' : '>',
}

def show(body):
    in_tag = False
    i = 0
    while i < len(body):
        if body[i] == '<':
            in_tag = True
        elif body[i] == '>':
            in_tag = False
        elif not in_tag:
            if body[i] == '&':
                end = body.find(';', i)
                if end != -1:
                    entity = body[i:end+1]
                    print(entity_map.get(entity, entity), end="")
                    i = end + 1
                    continue

            print(body[i], end="")
        i += 1
    print()

def source(body):
    print(body)

def load(url):
    body = url.request()
    if url.scheme != "view-source":
        show(body)
    else:
        source(body)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        import os
        default_path = os.path.abspath("debug.txt")
        url_string = f"file://{default_path}"
        load(URL(url_string))
        sys.exit()

    load(URL(" ".join(sys.argv[1:])))

