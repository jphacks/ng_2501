# -----------------------------------------------------------------------------
# PURPOSE
#   Discriminant D = b^2 - 4ac (a=1,b=0) controls x-axis intersections of
#   y = x^2 + c. Animate c: 2 -> 0 -> -3, show cases D<0, D=0, D>0 clearly.
#
# 0.18.1 NOTES
#   - x_range/y_range usage
#   - background via self.camera.background_color
#   - labels auto-fit into a rounded box; no overlaps
# -----------------------------------------------------------------------------

from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # ---------------------------- CONFIG ----------------------------------
        X_MIN, X_MAX, X_STEP = -3, 3, 1
        Y_MIN, Y_MAX, Y_STEP = -6, 14, 2
        AX_X_LEN, AX_Y_LEN = 6.0, 4.2
        a_val, b_val = 1.0, 0.0  # y = x^2 + c (a=1, b=0)
        EPS = 1e-6

        # ------------------------- LEFT: EXPLANATIONS -------------------------
        title = Text("Quadratic Function and Discriminant D", font_size=30, color=WHITE)
        formula = MathTex("y=ax^2+bx+c\\quad (a\\ne 0)").scale(0.9).set_color(WHITE)
        disc = MathTex("D=b^2-4ac").scale(0.9).set_color(WHITE)
        quad = MathTex("x=\\frac{-b\\pm\\sqrt{D}}{2a}").scale(0.9).set_color(WHITE)
        left_formula_grp = VGroup(formula, disc, quad).arrange(DOWN, aligned_edge=LEFT, buff=0.16)

        c_tracker = ValueTracker(2.0)  # start with c=2 (D<0)
        c_num = DecimalNumber(c_tracker.get_value(), num_decimal_places=2).scale(0.9).set_color(WHITE)
        param_row = VGroup(
            MathTex("a=1,").scale(0.9).set_color(WHITE),
            MathTex("\\;b=0,").scale(0.9).set_color(WHITE),
            VGroup(MathTex("\\;c=").scale(0.9).set_color(WHITE), c_num).arrange(RIGHT, buff=0.06),
        ).arrange(RIGHT, buff=0.14)

        D_num = DecimalNumber(0.0, num_decimal_places=2).scale(0.9).set_color(WHITE)
        D_label = VGroup(MathTex("D\\;=").scale(0.9).set_color(WHITE), D_num).arrange(RIGHT, buff=0.08)

        case_box = RoundedRectangle(corner_radius=0.15, width=5.6, height=1.0, color=GRAY_E).set_fill(
            color=GRAY, opacity=0.20
        )

        def fit_text_to_case_box(text_obj: Mobject, pad_w: float = 0.30, pad_h: float = 0.12) -> Mobject:
            """Scale and center a text so it fits inside case_box with padding."""
            max_w = case_box.width - pad_w
            max_h = case_box.height - pad_h
            if text_obj.width > 0 and text_obj.height > 0:
                scale_w = max_w / text_obj.width
                scale_h = max_h / text_obj.height
                text_obj.scale(min(scale_w, scale_h, 1.0))
            return text_obj.move_to(case_box.get_center())

        case_text = fit_text_to_case_box(Text("D < 0  →  No x-intercepts", color=RED, font_size=32))
        case_panel = VGroup(case_box, case_text)

        left_top = VGroup(title, left_formula_grp, param_row, D_label).arrange(DOWN, aligned_edge=LEFT, buff=0.22)

        # -------------------------- RIGHT: GRAPH ------------------------------
        axes = Axes(
            x_range=[X_MIN, X_MAX, X_STEP],
            y_range=[Y_MIN, Y_MAX, Y_STEP],
            x_length=AX_X_LEN,
            y_length=AX_Y_LEN,
            axis_config=dict(include_numbers=True, include_tip=False, stroke_color=GRAY_B, stroke_width=3),
        )
        axes.x_axis.set_stroke(width=3, color=WHITE)

        a, b = a_val, b_val

        def f(x: float) -> float:
            c = c_tracker.get_value()
            return a * x * x + b * x + c

        parabola_graph = always_redraw(lambda: axes.plot(lambda x: f(x), x_range=[X_MIN, X_MAX], color=YELLOW))

        def make_roots_group() -> VGroup:
            """Return dots/labels for x-intercepts as D changes."""
            c = c_tracker.get_value()
            D = b * b - 4 * a * c
            g = VGroup()
            if D > EPS:
                r = np.sqrt(D)
                x1 = (-b - r) / (2 * a)
                x2 = (-b + r) / (2 * a)
                for xv, name in ((x1, "x_1"), (x2, "x_2")):
                    if X_MIN <= xv <= X_MAX:
                        dot = Dot(axes.c2p(xv, 0), color=GREEN).scale(0.85)
                        dash = DashedLine(
                            axes.c2p(xv, 0), axes.c2p(xv, f(xv)), color=GREEN, dash_length=0.12, dashed_ratio=0.6
                        )
                        lbl = MathTex(name).scale(0.72).next_to(dot, DOWN, buff=0.06).set_color(WHITE)
                        g.add(dash, dot, lbl)
            elif abs(D) <= EPS:
                x0 = -b / (2 * a)
                if X_MIN <= x0 <= X_MAX:
                    d0 = Dot(axes.c2p(x0, 0), color=ORANGE).scale(0.95)
                    x0_label = MathTex("x_0").scale(0.72).next_to(d0, DOWN, buff=0.06).set_color(WHITE)
                    g.add(d0, x0_label)
            return g

        roots = always_redraw(make_roots_group)
        right_col = VGroup(axes, parabola_graph, roots)

        # ----------------------------- LAYOUT --------------------------------
        margin_x, margin_y = 0.6, 0.4
        column_gap = 0.8
        target_right_width = (config.frame_width - 2 * margin_x - column_gap) * 0.5
        right_col.scale(target_right_width / max(1e-6, right_col.width))
        left_col = VGroup(left_top, case_panel).arrange(DOWN, aligned_edge=LEFT, buff=0.24)
        layout = VGroup(left_col, right_col).arrange(RIGHT, buff=column_gap, aligned_edge=DOWN)

        max_w = config.frame_width - 2 * margin_x
        max_h = config.frame_height - 2 * margin_y
        layout.scale(min(max_w / layout.width, max_h / layout.height, 1.0)).move_to(ORIGIN)

        # ---------------------------- UPDATERS --------------------------------
        def update_D_and_c(_m=None):
            c = c_tracker.get_value()
            D = b * b - 4 * a * c
            c_num.set_value(c)
            D_num.set_value(D)
            if D > EPS:
                D_num.set_color(GREEN)
            elif D < -EPS:
                D_num.set_color(RED)
            else:
                D_num.set_color(ORANGE)

        c_num.add_updater(update_D_and_c)
        D_num.add_updater(update_D_and_c)

        # ------------------------- DRAW & ANIMATE -----------------------------
        self.add(layout)
        self.play(Create(axes), run_time=1.0)
        self.play(Create(parabola_graph), run_time=1.0)
        self.add(roots)
        self.wait(0.4)

        self.play(c_tracker.animate.set_value(0.0), run_time=2.0, rate_func=linear)
        case_text_eq = fit_text_to_case_box(Text("D = 0  →  Tangent (double root)", color=ORANGE, font_size=30))
        self.play(Transform(case_text, case_text_eq), run_time=0.5)
        self.play(Indicate(roots, color=ORANGE), run_time=0.9)

        self.play(c_tracker.animate.set_value(-3.0), run_time=2.0, rate_func=linear)
        case_text_gt = fit_text_to_case_box(Text("D > 0  →  Two intersections", color=GREEN, font_size=30))
        self.play(Transform(case_text, case_text_gt), run_time=0.5)
        self.play(Flash(roots, color=GREEN), run_time=0.9)
        self.wait(0.6)
