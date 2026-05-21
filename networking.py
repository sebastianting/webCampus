import socket
import sys
import ssl
import os

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]

        if self.scheme == "file":
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



def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        print("Please provide 1 url")
        sys.exit()
    elif len(sys.argv) == 1:
        default_path = os.path.abspath("debug.txt")
        url_string = f"file://{default_path}"
        load(URL(url_string))
        sys.exit()

    load(URL(sys.argv[1]))

