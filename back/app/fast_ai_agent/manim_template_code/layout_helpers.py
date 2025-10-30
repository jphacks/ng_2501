# -----------------------------------------------------------------------------
# PURPOSE
#   Small utility helpers for layout and clipping that are 0.19-safe.
#   NOTE: For code generation, prefer copying these functions into the output
#   file (no external imports). Keep this file only as a human-readable source.
# -----------------------------------------------------------------------------

from manim import *
import numpy as np

def fit_to_frame(mobj: Mobject, margins=(0.6, 0.4)) -> Mobject:
    """Scale+center mobj to fit into the frame with given (x,y) margins."""
    max_w = config.frame_width  - 2*margins[0]
    max_h = config.frame_height - 2*margins[1]
    if mobj.width == 0 or mobj.height == 0:
        return mobj.move_to(ORIGIN)
    scale = min(max_w / mobj.width, max_h / mobj.height, 1.0)
    mobj.scale(scale).move_to(ORIGIN)
    return mobj

def clip_line_to_box(m: float, b: float, xmin: float, xmax: float, ymin: float, ymax: float):
    """Return two points of y=mx+b clipped to the box; None if no visible segment."""
    cand = []
    # x borders
    for x in (xmin, xmax):
        y = m*x + b
        if ymin <= y <= ymax:
            cand.append((x, y))
    # y borders
    if abs(m) > 1e-12:
        for y in (ymin, ymax):
            x = (y - b) / m
            if xmin <= x <= xmax:
                cand.append((x, y))
    # unique
    uniq = []
    for p in cand:
        if all(abs(p[0]-q[0]) > 1e-9 or abs(p[1]-q[1]) > 1e-9 for q in uniq):
            uniq.append(p)
    if len(uniq) < 2:
        return None
    # pick farthest pair
    best = (uniq[0], uniq[1]); best_d = -1.0
    for i in range(len(uniq)):
        for j in range(i+1, len(uniq)):
            dx = uniq[i][0]-uniq[j][0]; dy = uniq[i][1]-uniq[j][1]
            d2 = dx*dx + dy*dy
            if d2 > best_d:
                best_d = d2; best = (uniq[i], uniq[j])
    return best

def safe_graph_label_outside_axes(axes: Axes, label: Mobject, where=UP, buff=0.22, align_edge=RIGHT):
    """Place label just outside the axes to avoid intersecting curves."""
    label.next_to(axes, where, buff=buff)
    label.align_to(axes, align_edge)
    return label
