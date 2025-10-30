# -----------------------------------------------------------------------------
# PURPOSE
#   Tangent line to y=x^2 at a moving point A. Right panel shows x and slope.
#
# 0.19-SAFE NOTES
#   - Use x_range/y_range (not x_min/x_max)
#   - Background set via self.camera.background_color
#   - No external imports besides manim/numpy/math
#   - Helper snippets are self-contained to allow copy-paste by generators
# -----------------------------------------------------------------------------

from manim import *
import numpy as np
import math

# ---- Helper snippets (copy if needed) ---------------------------------------
def fit_to_frame(mobj: Mobject, margins=(0.6, 0.4)) -> Mobject:
    """Scale+center mobj to fit into the frame with given (x,y) margins."""
    max_w = config.frame_width - 2 * margins[0]
    max_h = config.frame_height - 2 * margins[1]
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
        y = m * x + b
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
        if all(abs(p[0] - q[0]) > 1e-9 or abs(p[1] - q[1]) > 1e-9 for q in uniq):
            uniq.append(p)
    if len(uniq) < 2:
        return None
    # pick farthest pair
    best = (uniq[0], uniq[1])
    best_d = -1.0
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            dx = uniq[i][0] - uniq[j][0]
            dy = uniq[i][1] - uniq[j][1]
            d2 = dx * dx + dy * dy
            if d2 > best_d:
                best_d = d2
                best = (uniq[i], uniq[j])
    return best

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # ---------------------------- CONFIG ----------------------------------
        X_MIN, X_MAX, X_STEP = -3, 3, 1
        Y_MIN, Y_MAX, Y_STEP = -1, 10, 2
        AX_X_LEN, AX_Y_LEN = 6.0, 6.0
        START_X, END_X = -2.5, 2.5
        EPS = 1e-6

        # ------------------------- LEFT: GRAPH PANEL --------------------------
        axes = Axes(
            x_range=[X_MIN, X_MAX, X_STEP],
            y_range=[Y_MIN, Y_MAX, Y_STEP],
            x_length=AX_X_LEN,
            y_length=AX_Y_LEN,
            axis_config={"include_numbers": True, "include_tip": False, "stroke_color": GRAY_B, "stroke_width": 3},
        )
        x_label = axes.get_x_axis_label(Text("x", color=WHITE))
        y_label = axes.get_y_axis_label(Text("y", color=WHITE)).next_to(axes.y_axis, LEFT, buff=0.2)

        # Define the function and its derivative
        def f(x):
            return x**2

        def df(x):
            return 2 * x

        parabola = axes.plot(f, x_range=[X_MIN, X_MAX], color=YELLOW)
        parabola_label = Text("y = x^2", font_size=28, color=YELLOW)
        parabola_label.next_to(axes, UP, buff=0.18).align_to(axes, RIGHT)

        x_tracker = ValueTracker(START_X)

        point_A = always_redraw(
            lambda: Dot(
                axes.c2p(x_tracker.get_value(), f(x_tracker.get_value())),
                color=WHITE
            ).scale(0.9)
        )
        label_A = always_redraw(
            lambda: Text("A", font_size=28, color=WHITE).next_to(point_A, UR, buff=0.1)
        )

        def create_tangent_line():
            x_val = x_tracker.get_value()
            y_val = f(x_val)
            slope = df(x_val)
            y_intercept = y_val - slope * x_val
            pts = clip_line_to_box(slope, y_intercept, X_MIN, X_MAX, Y_MIN, Y_MAX)
            if pts:
                (x1, y1), (x2, y2) = pts
                color = RED if slope > EPS else (BLUE if slope < -EPS else GRAY_B)
                return Line(
                    axes.c2p(x1, y1), axes.c2p(x2, y2),
                    color=color, stroke_width=4
                )
            return VGroup()

        tangent_line = always_redraw(create_tangent_line)
        left_panel = VGroup(axes, x_label, y_label, parabola, parabola_label, point_A, label_A, tangent_line)

        # ------------------------- RIGHT: TEXT PANEL --------------------------
        x_text = MathTex("x = ").scale(1.2).set_color(WHITE)
        slope_text = MathTex(r"\text{slope} = ").scale(1.2).set_color(WHITE)
        x_value = DecimalNumber(x_tracker.get_value(), num_decimal_places=2).scale(1.2).set_color(WHITE)
        slope_value = DecimalNumber(df(x_tracker.get_value()), num_decimal_places=2).scale(1.2).set_color(WHITE)
        x_value.add_updater(lambda m: m.set_value(x_tracker.get_value()))
        slope_value.add_updater(lambda m: m.set_value(df(x_tracker.get_value())))
        x_row = VGroup(x_text, x_value).arrange(RIGHT, buff=0.15)
        slope_row = VGroup(slope_text, slope_value).arrange(RIGHT, buff=0.15)
        right_panel = VGroup(x_row, slope_row).arrange(DOWN, aligned_edge=LEFT, buff=0.8)

        # ----------------------------- LAYOUT --------------------------------
        layout = VGroup(left_panel, right_panel).arrange(RIGHT, buff=1.2, aligned_edge=UP)
        fit_to_frame(layout, margins=(0.6, 0.4))

        # ------------------------- DRAW & ANIMATE ----------------------------
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=1.2)
        self.play(Create(parabola), FadeIn(parabola_label, shift=UP*0.1), run_time=1.0)
        self.add(point_A, label_A, tangent_line)
        self.play(FadeIn(right_panel, shift=LEFT), run_time=0.6)
        self.play(x_tracker.animate.set_value(END_X), run_time=6, rate_func=linear)
        self.wait(0.6)
