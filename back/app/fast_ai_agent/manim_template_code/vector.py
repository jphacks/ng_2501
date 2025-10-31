# -----------------------------------------------------------------------------
# PURPOSE
#   Parallelogram rule: show A, B, A+B with robust dashed guides and
#   stable numeric readouts (A=(ax,ay), B=(bx,by), A+B=(...)).
#
# 0.19-SAFE NOTES
#   - DashedVMobject(..., num_dashes=...) helper for 0.19 compatibility
#   - Background via self.camera.background_color (BLACK)
#   - Right readout panel pinned at DR to avoid overlaps with the plane
# -----------------------------------------------------------------------------

from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # === Trackers for A=(ax,ay), B=(bx,by) in *axis* coordinates ===
        ax, ay = ValueTracker(2.0), ValueTracker(1.0)
        bx, by = ValueTracker(1.0), ValueTracker(2.0)

        # === Left: coordinate plane (with numbers) ===
        plane = NumberPlane(
            x_range=[-7, 7, 1],
            y_range=[-4, 4, 1],
            background_line_style=dict(stroke_color=GRAY_D, stroke_opacity=0.35, stroke_width=1.4),
            axis_config=dict(stroke_color=GRAY_B, stroke_width=3),
        )
        plane.add_coordinates()  # numbers will be white on black by default
        plane.scale_to_fit_width(config.frame_width * 0.78).to_edge(LEFT, buff=0.12)
        axis_labels = plane.get_axis_labels(Text("x", color=WHITE), Text("y", color=WHITE))

        def P(x, y):
            return plane.c2p(x, y)

        def A():
            return np.array([ax.get_value(), ay.get_value(), 0.0])

        def B():
            return np.array([bx.get_value(), by.get_value(), 0.0])

        arrowA = always_redraw(
            lambda: Arrow(P(0, 0), P(*A()[:2]), buff=0, max_tip_length_to_length_ratio=0.12, stroke_width=7, color=BLUE)
        )
        arrowB = always_redraw(
            lambda: Arrow(
                P(0, 0), P(*B()[:2]), buff=0, max_tip_length_to_length_ratio=0.12, stroke_width=7, color=GREEN
            )
        )
        arrowA_at_B = always_redraw(
            lambda: Arrow(
                P(*B()[:2]),
                P(*(B()[:2] + A()[:2])),
                buff=0,
                max_tip_length_to_length_ratio=0.12,
                stroke_width=4,
                color=BLUE_D,
                stroke_opacity=0.9,
            )
        )
        arrowB_at_A = always_redraw(
            lambda: Arrow(
                P(*A()[:2]),
                P(*(A()[:2] + B()[:2])),
                buff=0,
                max_tip_length_to_length_ratio=0.12,
                stroke_width=4,
                color=GREEN_D,
                stroke_opacity=0.9,
            )
        )
        arrowSum = always_redraw(
            lambda: Arrow(
                P(0, 0),
                P(*(A()[:2] + B()[:2])),
                buff=0,
                max_tip_length_to_length_ratio=0.12,
                stroke_width=7,
                color=YELLOW,
            )
        )

        # === Dashed helpers (v0.19: use num_dashes) ===
        def dashed_line(p1, p2, color=WHITE, width=2, dashed_ratio=0.55, density=8, z=5):
            base = Line(p1, p2)
            n = max(2, int(base.get_length() * density))
            dv = DashedVMobject(base, num_dashes=n, dashed_ratio=dashed_ratio)
            dv.set_stroke(color=color, width=width, opacity=1.0).set_z_index(z)
            return dv

        def dashed_polygon(points, color=WHITE, width=2, dashed_ratio=0.55, n=60, z=4):
            poly = Polygon(*points)
            dv = DashedVMobject(poly, num_dashes=n, dashed_ratio=dashed_ratio)
            dv.set_stroke(color=color, width=width, opacity=0.95).set_z_index(z)
            return dv

        guide_B_from_A = always_redraw(
            lambda: dashed_line(
                P(*A()[:2]), P(*(A()[:2] + B()[:2])), color=GREEN, width=3, dashed_ratio=0.55, density=8, z=6
            )
        )
        guide_A_from_B = always_redraw(
            lambda: dashed_line(
                P(*B()[:2]), P(*(B()[:2] + A()[:2])), color=BLUE, width=3, dashed_ratio=0.55, density=8, z=6
            )
        )
        para_outline = always_redraw(
            lambda: dashed_polygon(
                [P(0, 0), P(*A()[:2]), P(*(A()[:2] + B()[:2])), P(*B()[:2])],
                color=WHITE,
                width=2,
                dashed_ratio=0.55,
                n=60,
                z=4,
            )
        )
        para_fill = always_redraw(
            lambda: Polygon(
                P(0, 0),
                P(*A()[:2]),
                P(*(A()[:2] + B()[:2])),
                P(*B()[:2]),
                stroke_color=WHITE,
                stroke_opacity=0.85,
                stroke_width=2,
                fill_color=YELLOW,
                fill_opacity=0.12,
            ).set_z_index(1)
        )

        labelA = always_redraw(lambda: Text("A", font_size=36, color=BLUE).next_to(arrowA.get_end(), UR, buff=0.18))
        labelB = always_redraw(lambda: Text("B", font_size=36, color=GREEN).next_to(arrowB.get_end(), UR, buff=0.18))
        labelS = always_redraw(
            lambda: Text("A+B", font_size=36, color=YELLOW).next_to(arrowSum.get_end(), UL, buff=0.18)
        )

        def spacer(w=0.14):
            return Rectangle(width=w, height=0.001).set_stroke(opacity=0).set_fill(opacity=0)

        def vector_row_stable(
            name, color, tx: ValueTracker, ty: ValueTracker, name_size=26, num_size=36, buff=0.16, close_gap=0.06
        ):
            name_text = Text(f"{name} = (", font_size=name_size, color=GRAY_B)
            comma = Text(",", font_size=name_size, color=WHITE)
            rpar = Text(")", font_size=name_size, color=WHITE)
            dx = DecimalNumber(0.0, num_decimal_places=2, include_sign=False, font_size=num_size, color=color)
            dy = DecimalNumber(0.0, num_decimal_places=2, include_sign=False, font_size=num_size, color=color)
            dx.add_updater(lambda d: d.set_value(tx.get_value()))
            dy.add_updater(lambda d: d.set_value(ty.get_value()))
            row = VGroup(
                name_text,
                VGroup(dx, spacer(0.16)).arrange(RIGHT, buff=0),
                comma,
                VGroup(dy, spacer(close_gap)).arrange(RIGHT, buff=0),
                rpar,
            ).arrange(RIGHT, buff=buff)
            return row

        rowA = vector_row_stable("A", BLUE, ax, ay, close_gap=0.06)
        rowB = vector_row_stable("B", GREEN, bx, by, close_gap=0.06)

        sx = DecimalNumber(0.0, num_decimal_places=2, include_sign=False, font_size=38, color=YELLOW)
        sy = DecimalNumber(0.0, num_decimal_places=2, include_sign=False, font_size=38, color=YELLOW)
        sx.add_updater(lambda d: d.set_value(ax.get_value() + bx.get_value()))
        sy.add_updater(lambda d: d.set_value(ay.get_value() + by.get_value()))
        sum_label = Text("A+B = (", font_size=26, color=GRAY_B)
        sum_comma = Text(",", font_size=26, color=WHITE)
        sum_rpar = Text(")", font_size=26, color=WHITE)
        rowS = VGroup(
            sum_label,
            VGroup(sx, spacer(0.16)).arrange(RIGHT, buff=0),
            sum_comma,
            VGroup(sy, spacer(0.06)).arrange(RIGHT, buff=0),
            sum_rpar,
        ).arrange(RIGHT, buff=0.16)

        right_panel = VGroup(rowA, rowB, rowS).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
        right_panel.scale_to_fit_width(config.frame_width * 0.22)
        right_panel.to_corner(DR, buff=0.28)

        separator = Line(UP * 3.6, DOWN * 3.6).set_stroke(color=GRAY_B, width=2, opacity=0.7)
        separator.move_to((plane.get_right() + right_panel.get_left()) / 2)

        # === Intro & animations ===
        self.play(FadeIn(plane), FadeIn(axis_labels), run_time=0.6)
        self.play(Create(arrowA), FadeIn(labelA), Create(arrowB), FadeIn(labelB), run_time=1.2)
        self.play(Create(guide_B_from_A), Create(guide_A_from_B), run_time=0.9)
        self.play(Create(para_outline), run_time=0.8)
        self.play(Create(arrowB_at_A), Create(arrowA_at_B), run_time=0.8)

        diag = dashed_line(P(0, 0), P(*(A()[:2] + B()[:2])), color=YELLOW, width=3, dashed_ratio=0.55, density=8, z=7)
        self.play(Create(diag), run_time=0.6)
        self.play(FadeOut(diag), Create(arrowSum), FadeIn(labelS), run_time=0.8)

        self.play(FadeIn(para_fill, shift=UP * 0.05), run_time=0.5)
        self.play(
            LaggedStart(
                FadeIn(rowA, shift=RIGHT * 0.12),
                FadeIn(rowB, shift=RIGHT * 0.12),
                FadeIn(rowS, shift=RIGHT * 0.12),
                lag_ratio=0.15,
                run_time=0.9,
            ),
            FadeIn(separator),
        )
        self.play(FadeOut(guide_A_from_B), FadeOut(guide_B_from_A), FadeOut(para_outline), run_time=0.4)

        def drag(Ax_, Ay_, Bx_, By_, t=3.8):
            self.play(
                ax.animate.set_value(Ax_),
                ay.animate.set_value(Ay_),
                bx.animate.set_value(Bx_),
                by.animate.set_value(By_),
                rate_func=linear,
                run_time=t,
            )

        drag(-1.5, 2.2, 2.0, -0.8, t=4.0)
        drag(-3.2, -0.6, -1.1, 1.8, t=4.0)
        drag(-2.5, -1.8, 2.6, -0.4, t=4.0)
        drag(1.4, 1.2, 1.8, 0.3, t=4.0)
        drag(0.8, -0.5, -0.6, -2.8, t=4.0)

        self.play(arrowSum.animate.set_stroke(width=9), run_time=0.25)
        self.play(arrowSum.animate.set_stroke(width=7), run_time=0.25)
        self.wait(0.8)
