# -----------------------------------------------------------------------------
# PURPOSE
#   Reference scene for the parabola y = a x^2 + b x + c.
#   Left: axes + live parabola, vertex helper.
#   Right: stable readout panel (a, b, c, and Vertex) with non-overlapping
#   numbers that stay anchored next to their labels while values update.
#
# COMPAT NOTES (Manim Community v0.19)
#   - Use x_range / y_range (no x_min/x_max).
#   - Prefer MathTex for math content to avoid “Missing $” errors.
#   - Keep DecimalNumber sizes via constructor (font_size=...) or set(...).
#   - Anchored updaters reposition values every frame to prevent overlap.
#
# HOW TO RUN
#   manim -ql main.py GeneratedScene
# -----------------------------------------------------------------------------

from manim import *


class GeneratedScene(Scene):
    def construct(self) -> None:
        # --- animated parameters (ValueTrackers) ---
        a_tracker = ValueTracker(1.0)
        b_tracker = ValueTracker(-2.0)
        c_tracker = ValueTracker(-1.0)

        # --- axes + parabola on the left (keep prior placement) ---
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            x_length=5,
            y_length=5,
            axis_config={"include_numbers": True, "font_size": 28, "include_tip": False},
        ).to_edge(LEFT, buff=0.8)

        # Smaller axis labels; place "y" at the upper-left of the y-axis tip
        x_label = axes.get_x_axis_label(Text("x", font_size=20))
        y_label = Text("y", font_size=20)
        y_label.next_to(axes.y_axis.get_top(), UL, buff=0.12)

        def parabola_func(x: float) -> float:
            a = a_tracker.get_value()
            b = b_tracker.get_value()
            c = c_tracker.get_value()
            return a * x * x + b * x + c

        parabola = axes.plot(
            lambda x: parabola_func(x),
            x_range=[-4, 4],
            color=YELLOW,
            stroke_width=4,
        )
        # Update the curve whenever a/b/c change
        parabola.add_updater(
            lambda m: m.become(
                axes.plot(
                    lambda x: parabola_func(x),
                    x_range=[-4, 4],
                    color=YELLOW,
                    stroke_width=4,
                )
            )
        )

        # Helper to compute the vertex (used by the right panel)
        def compute_vertex() -> tuple[float, float]:
            a = a_tracker.get_value()
            b = b_tracker.get_value()
            c = c_tracker.get_value()
            xv = 0.0 if abs(a) < 1e-8 else -b / (2.0 * a)
            yv = a * xv * xv + b * xv + c
            return xv, yv

        self.add(axes, x_label, y_label, parabola)

        # --- right-side information panel (same placement) ---
        right_panel = self.build_info_panel(a_tracker, b_tracker, c_tracker, compute_vertex)
        right_panel.to_edge(RIGHT, buff=0.8)
        self.add(right_panel)

        # ===================== Parameter phases =====================
        # Animate "a only" (shape / flip)
        self.play(a_tracker.animate.set_value(0.5), run_time=1.6, rate_func=smooth)
        self.play(a_tracker.animate.set_value(1.8), run_time=1.6, rate_func=smooth)
        self.play(a_tracker.animate.set_value(1.0), run_time=1.2, rate_func=smooth)
        self.wait(0.4)

        # Animate "b only" (horizontal shift)
        self.play(b_tracker.animate.set_value(2.0), run_time=1.8, rate_func=linear)
        self.play(b_tracker.animate.set_value(-3.0), run_time=1.8, rate_func=linear)
        self.play(b_tracker.animate.set_value(-2.0), run_time=1.2, rate_func=smooth)
        self.wait(0.4)

        # Animate "c only" (vertical shift)
        self.play(c_tracker.animate.set_value(2.0), run_time=1.8, rate_func=linear)
        self.play(c_tracker.animate.set_value(-2.0), run_time=1.8, rate_func=linear)
        self.play(c_tracker.animate.set_value(-1.0), run_time=1.2, rate_func=smooth)
        self.wait(0.6)

    # -------------------------- UI builder --------------------------
    def build_info_panel(
        self,
        a_tracker: ValueTracker,
        b_tracker: ValueTracker,
        c_tracker: ValueTracker,
        compute_vertex: callable,
    ) -> VGroup:
        """
        Create a boxed panel containing:
          y = a x^2 + b x + c
          a = <...>
          b = <...>
          c = <...>
          Vertex = ( <xv>, <yv> )
        Values update live and remain anchored next to their labels.
        """
        # Title + frame
        title = Text("Parameters & Vertex", font_size=30)
        box = RoundedRectangle(corner_radius=0.2, width=5.5, height=4.2, stroke_width=2, color=WHITE)

        # Equation line (1 size up as requested)
        eq_line = MathTex(r"y = a x^2 + b x + c", font_size=32)

        # a, b, c lines (labels + values; 1 size up)
        a_line = self._name_value_row(r"a =", a_tracker, font_size=32)
        b_line = self._name_value_row(r"b =", b_tracker, font_size=32)
        c_line = self._name_value_row(r"c =", c_tracker, font_size=32)

        # Vertex line built from parts to keep layout stable
        vertex_label = Text("Vertex =", font_size=28)
        lpar = Text("(", font_size=28)
        vx = DecimalNumber(0, num_decimal_places=2, font_size=28)
        comma = Text(",", font_size=28)
        vy = DecimalNumber(0, num_decimal_places=2, font_size=28)
        rpar = Text(")", font_size=28)

        # Initial placement (maintained by updaters below)
        vertex_label.next_to(box.get_left(), RIGHT, buff=0.4)
        lpar.next_to(vertex_label, RIGHT, buff=0.2)
        vx.next_to(lpar, RIGHT, buff=0.12)
        comma.next_to(vx, RIGHT, buff=0.12)
        vy.next_to(comma, RIGHT, buff=0.12)
        rpar.next_to(vy, RIGHT, buff=0.12)

        # Updaters: update both the numbers and their anchored positions
        def _upd_vx(m: DecimalNumber) -> None:
            xv, _ = compute_vertex()
            m.set_value(xv)
            m.next_to(lpar, RIGHT, buff=0.12)

        def _upd_vy(m: DecimalNumber) -> None:
            _, yv = compute_vertex()
            m.set_value(yv)
            m.next_to(comma, RIGHT, buff=0.12)

        vx.add_updater(_upd_vx)
        comma.add_updater(lambda m: m.next_to(vx, RIGHT, buff=0.12))
        vy.add_updater(_upd_vy)
        rpar.add_updater(lambda m: m.next_to(vy, RIGHT, buff=0.12))

        vertex_line = VGroup(vertex_label, lpar, vx, comma, vy, rpar)

        # Stack lines under the title and place inside the box
        title.next_to(box.get_top(), DOWN, buff=0.3)
        body = VGroup(eq_line, a_line, b_line, c_line, vertex_line).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        body.next_to(title, DOWN, aligned_edge=LEFT, buff=0.4)
        body.shift(RIGHT * 0.2)  # inner left padding

        return VGroup(box, title, body)

    def _name_value_row(self, name_tex: str, tracker: ValueTracker, font_size: int = 28) -> VGroup:
        """
        Build a single row like:  a = 1.23
        The DecimalNumber is updated every frame and kept anchored to the label.
        """
        name = MathTex(name_tex, font_size=font_size)
        val = DecimalNumber(tracker.get_value(), num_decimal_places=2, font_size=font_size)

        # Initial placement (kept by the updater)
        val.next_to(name, RIGHT, buff=0.2).align_to(name, DOWN)

        # Anchored updater: update value and reposition next to the name
        def _upd(m: DecimalNumber) -> None:
            m.set_value(tracker.get_value())
            m.next_to(name, RIGHT, buff=0.2).align_to(name, DOWN)

        val.add_updater(_upd)
        return VGroup(name, val)
