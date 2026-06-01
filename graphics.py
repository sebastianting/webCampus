import tkinter
import tkinter.font
from networking import URL, lex, source, Text, Tag

WIDTH, HEIGHT = 800, 600

HSTEP, VSTEP = 13, 18

SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=1)
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.onscroll)
        self.window.bind("<Configure>", self.resize)
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def load(self, url):
        body = url.request()
        if url.scheme == "view-source":
            self.text = source(body)
        elif url.scheme == "about":
            if body == "blank":
                self.text = [""]
        else:
            self.text = lex(body)
        self.display_list = layout(self.text)
        self.max_height = self.display_list[-1][1]
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c, anchor = "nw", font=f)

        if self.max_height > HEIGHT:
            thumb_height = HEIGHT * HEIGHT / self.max_height
            thumb_top = self.scroll * HEIGHT / self.max_height
            thumb_bot = thumb_top + thumb_height
            self.canvas.create_rectangle(WIDTH - HSTEP, thumb_top, WIDTH, thumb_bot, fill='#5A99F0', width=0, activefill='#63BFF5')

    def onscroll(self, e):
        if e.delta > 0:
            self.scrolldown(e)
        else:
            self.scrollup(e)

    def scrolldown(self, e=None):
        global SCROLLBAR_BOT, SCROLLBAR_TOP
        if e.delta:
            if self.scroll + e.delta > self.max_height: self.scroll = self.max_height
            else: self.scroll += e.delta * 4
        else:
            if self.scroll + SCROLL_STEP > self.max_height: self.scroll = self.max_height
            else: self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, e=None):
        if e.delta:
            if self.scroll + e.delta < 0 : self.scroll = 0
            else: self.scroll += e.delta * 4
        else:
            if self.scroll - SCROLL_STEP < 0: self.scroll = 0
            else : self.scroll -= SCROLL_STEP
        self.draw()

    def resize(self, e):
        global WIDTH, HEIGHT
        WIDTH = e.width
        HEIGHT = e.height
        self.display_list = layout(self.text)
        self.max_height = self.display_list[-1][1]
        self.draw()

    def on_click(self, e):
        self.dragging = e.x >= WIDTH - HSTEP

    def on_drag(self, e):
        if self.dragging:
            self.scroll = max(0, min(e.y * self.max_height / HEIGHT, self.max_height - HEIGHT))
            self.draw()

def layout(tokens):
    font = tkinter.font.Font()
    display_list = []

    weight = "normal"
    style = "roman"

    cursor_x, cursor_y = HSTEP, VSTEP
    for tok in tokens:
        if isinstance(tok, Text):
            for word in tok.text.split():
                font = tkinter.font.Font(
                    size=16,
                    weight=weight,
                    slant=style,
                )
                w = font.measure(word)
                if cursor_x + w > WIDTH - HSTEP:
                    cursor_y += font.metrics("linespace") * 1.25
                    cursor_x = HSTEP
                display_list.append((cursor_x, cursor_y, word, font))
                cursor_x += w + font.measure(" ")
        elif tok.tag == "i":
            style = "italic"
        elif tok.tag == "/i":
            style = "roman"
        elif tok.tag == "b":
            weight = "bold"
        elif tok.tag == "/b":
            weight = "normal"

    return display_list

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

