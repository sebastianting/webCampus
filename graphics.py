import tkinter
import tkinter.font
from networking import URL, source, Text, Element, HTMLParser, print_tree

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
        if url.scheme == "view-source": # FIXME: adapt to the tree method
            self.nodes = source(body)
        elif url.scheme == "about":
            if body == "blank":
                self.nodes = []
        else:
            self.nodes = HTMLParser(body).parse()

        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.max_height = self.document.height
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)

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
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.max_height = self.document.height
        self.draw()

    def on_click(self, e):
        self.dragging = e.x >= WIDTH - HSTEP

    def on_drag(self, e):
        if self.dragging:
            self.scroll = max(0, min(e.y * self.max_height / HEIGHT, self.max_height - HEIGHT))
            self.draw()

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

class BlockLayout:
    def __init__(self, nodes, parent, previous):
        self.nodes = nodes # we take multiple nodes the case of anonymous block boxes
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.display_list = []
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        if len(self.nodes) == 1:
            node = self.nodes[0]
            if isinstance(node, Element) and node.tag == "li":
                self.x = self.x + 2 * HSTEP
                self.width = self.width - 2 * HSTEP

        mode = self.layout_mode()
        if mode == "block":
            node = self.nodes[0]
            previous = None
            inline_nodes = []
            for child in node.children:
                if (isinstance(child, Element) and child.tag not in BLOCK_ELEMENTS) \
                    or isinstance(child, Text):
                    inline_nodes.append(child)

                else:
                    if inline_nodes:
                        next = BlockLayout(inline_nodes, self, previous)
                        self.children.append(next)
                        previous = next
                        inline_nodes = []

                    next = BlockLayout([child], self, previous)
                    self.children.append(next)
                    previous = next
            if inline_nodes:
                next = BlockLayout(inline_nodes, self, previous)
                self.children.append(next)
                previous = next

            for child in self.children:
                child.layout()

            self.height = sum([
                child.height for child in self.children
            ])
        else:
            self.display_list = []
            self.line = []
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12
            self.centered = False
            print("INLINE NODES ", self.nodes)
            for node in self.nodes:
                print("RECURSNG", node)
                self.recurse(node)
            self.flush()
            self.height = self.cursor_y

    def layout_mode(self):
        node = self.nodes[0]
        if len(self.nodes) != 1:
            return "inline"
        if isinstance(node, Text):
            return "inline"
        elif any ([isinstance(child, Element) and \
                   child.tag in BLOCK_ELEMENTS
                for child in node.children]):
            return "block"
        elif node.children:
            return "inline"
        else:
            return "block"

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
        elif tag.startswith("h1"): # not mentioned in book, may break
            self.centered = True

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "h1":
            self.flush()
            self.centered = False

    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def paint(self):
        cmds = []
        node = self.nodes[0]
        if len(self.nodes) == 1:

            if isinstance(node, Element) and node.tag == "pre":
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.x, self.y, x2, y2, "gray")
                cmds.append(rect)
            if isinstance(node, Element) and node.tag == "nav":
                if self.node.attributes.get("class") == "links":

                    x2, y2 = self.x + self.width, self.y + self.height
                    rect = DrawRect(self.x, self.y, x2, y2, "gray")
                    cmds.append(rect)
            if isinstance(node, Element) and node.tag == "li":
                x1, y1 = self.x - HSTEP, self.y + 8
                x2, y2 = x1 + 5, y1 + 5
                rect = DrawRect(x1, y1, x2, y2, "gray")
                cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))
        return cmds


    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > self.width:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font, in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
            if self.centered:
                offset = (WIDTH - HSTEP - self.cursor_x) / 2
                x += offset
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []

class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw')

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color 
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0, fill=self.color)

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        child = BlockLayout([self.node], self, None)
        self.children.append(child)
        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []

FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
                                 slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

