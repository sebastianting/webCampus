import tkinter
from networking import URL, lex, source

WIDTH, HEIGHT = 800, 600

HSTEP, VSTEP = 13, 18

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url):
        body = url.request()
        if url.scheme != "view-source":
            text = lex(body)
        else:
            text = source(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        SCROLL_STEP = 100
        self.scroll += SCROLL_STEP
        self.draw()

        
    #    HSTEP, VSTEP = 13, 18
    #    cursor_x, cursor_y = HSTEP, VSTEP
    #    for c in text:
    #        self.canvas.create_text(cursor_x, cursor_y, text=c)
    #        cursor_x += HSTEP
    #        if cursor_x >= WIDTH - HSTEP:
    #            cursor_y += VSTEP
    #            cursor_x = HSTEP

def layout(text):
    display_list = []

    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

