import socket
import ssl

class URL:
    def __init__(self, url):
        if "://" in url:
            self.scheme, url = url.split("://", 1)
            assert self.scheme in ["http", "https", "file"]
        elif ":" in url:
            self.scheme, url = url.split(":", 1)
            assert self.scheme in ["data"]
            self.mediatype, self.body = url.split(",", 1)

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

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if ":" in self.headers["Host"]:
            self.headers["Host"], port= self.headers["Host"].split(":", 1)
            self.port = int(port)

 

    def request(self):
        if self.scheme == "file":
            with open(self.path, 'r', encoding="utf-8") as file:
                return file.read()

        if self.scheme == "data":
            return self.body

        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        self.headers |= {"Connection" : "close"}
        self.headers |= {"User-Agent" : "25Ting following browser.engineering"}

        s.connect((self.headers["Host"], self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.headers["Host"])

        request = "GET {} HTTP/1.0\r\n".format(self.path)
        for name, value in self.headers.items():
            request += "{}: {}\r\n".format(name, value)
        request += "\r\n"
        s.send(request.encode("utf8"))

        response = s.makefile("r", encoding="utf8",  newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content

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
                end = body.find(';')
                if end != -1:
                    entity = body[i:end+1]
                    print(entity_map.get(entity, entity), end="")
                    i = end + 1
                    continue

            print(body[i], end="")
        i += 1
    print()

def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        import os
        default_path = os.path.abspath("debug.txt")
        url_string = f"file://{default_path}"
        load(URL(url_string))
        sys.exit()

    load(URL(" ".join(sys.argv[1:])))

