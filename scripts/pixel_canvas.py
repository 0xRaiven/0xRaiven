"""2x2 pixel-grid buffer with horizontal run-length encoding for compact crispEdges SVG."""


class PixelCanvas:
    """Sparse 2D pixel grid that merges adjacent same-color horizontal pixels into single <rect> spans."""

    def __init__(self, size=2):
        self.size = size
        self.cells = {}

    def put(self, gx, gy, color):
        self.cells[(int(gx), int(gy))] = color

    def hline(self, gx0, gx1, gy, color):
        step = 1 if gx1 >= gx0 else -1
        for gx in range(int(gx0), int(gx1) + step, step):
            self.cells[(gx, int(gy))] = color

    def to_svg(self):
        if not self.cells:
            return ""
        rows = {}
        for (gx, gy), col in self.cells.items():
            rows.setdefault(gy, []).append((gx, col))
        out = []
        s = self.size
        for gy in sorted(rows):
            row = sorted(rows[gy], key=lambda item: item[0])
            run_x, run_col = row[0]
            run_len = 1
            for gx, col in row[1:]:
                if gx == run_x + run_len and col == run_col:
                    run_len += 1
                else:
                    out.append(
                        f'<rect x="{run_x * s}" y="{gy * s}" width="{run_len * s}" height="{s}" fill="{run_col}"/>'
                    )
                    run_x, run_col, run_len = gx, col, 1
            out.append(
                f'<rect x="{run_x * s}" y="{gy * s}" width="{run_len * s}" height="{s}" fill="{run_col}"/>'
            )
        return "\n    ".join(out)


def px_rect(x, y, color, cls="", size=2):
    """Render a single pixel <rect> with an optional CSS class."""
    c = f' class="{cls}"' if cls else ""
    return f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}"{c}/>'
