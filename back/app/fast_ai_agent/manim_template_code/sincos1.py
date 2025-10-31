# -----------------------------------------------------------------------------
# PURPOSE
#   Synchronize a moving point on the unit circle with graphs of sin and cos.
#   π-ticks on the right; projections and arc on the left.
#
# 0.18.1 NOTES
#   - Radians throughout (TAU)
#   - Background via self.camera.background_color (BLACK)
#   - Dynamic vertical alignment so y=0 aligns across panels
# -----------------------------------------------------------------------------

from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # ---------------------------- CONFIG ----------------------------------
        SIN_COLOR, COS_COLOR, THETA_COLOR = RED, BLUE, YELLOW
        theta = ValueTracker(0.0)
        X_MIN, X_MAX = 0, TAU

        # -------------------------- LEFT: CIRCLE ------------------------------
        left_axes = Axes(
            x_range=[-1.2, 1.2, 0.5],
            y_range=[-1.2, 1.2, 0.5],
            x_length=4.6,
            y_length=4.6,
            axis_config=dict(include_numbers=True, include_tip=False, stroke_color=GRAY_B, stroke_width=3),
        )
        unit_circle = ParametricFunction(
            lambda t: left_axes.c2p(np.cos(t), np.sin(t)),
            t_range=[0, TAU],
            color=WHITE,
            stroke_width=3,
        )

        def P_xy() -> tuple[float, float]:
            t = theta.get_value()
            return (np.cos(t), np.sin(t))

        P_dot = always_redraw(lambda: Dot(left_axes.c2p(*P_xy()), color=WHITE).scale(0.7))
        OP = always_redraw(lambda: Line(left_axes.c2p(0, 0), left_axes.c2p(*P_xy()), color=THETA_COLOR, stroke_width=4))

        cos_segment = always_redraw(
            lambda: Line(
                left_axes.c2p(0, 0), left_axes.c2p(np.cos(theta.get_value()), 0), color=COS_COLOR, stroke_width=6
            )
        )
        sin_segment = always_redraw(
            lambda: Line(
                left_axes.c2p(0, 0), left_axes.c2p(0, np.sin(theta.get_value())), color=SIN_COLOR, stroke_width=6
            )
        )

        v_drop = always_redraw(
            lambda: DashedLine(
                left_axes.c2p(*P_xy()),
                left_axes.c2p(np.cos(theta.get_value()), 0),
                color=COS_COLOR,
                dash_length=0.08,
                dashed_ratio=0.6,
            )
        )
        h_drop = always_redraw(
            lambda: DashedLine(
                left_axes.c2p(*P_xy()),
                left_axes.c2p(0, np.sin(theta.get_value())),
                color=SIN_COLOR,
                dash_length=0.08,
                dashed_ratio=0.6,
            )
        )

        arc = always_redraw(
            lambda: ParametricFunction(
                lambda t: left_axes.c2p(np.cos(t), np.sin(t)),
                t_range=[0, max(0.001, min(theta.get_value(), TAU))],
                color=THETA_COLOR,
            ).set_stroke(width=4)
        )

        left_legend = (
            VGroup(
                MathTex("\\sin\\theta").scale(0.8).set_color(SIN_COLOR),
                MathTex("\\cos\\theta").scale(0.8).set_color(COS_COLOR),
            )
            .arrange(RIGHT, buff=0.6)
            .next_to(left_axes, UP, buff=0.25)
        )

        left_panel = VGroup(
            left_axes, unit_circle, OP, P_dot, v_drop, h_drop, cos_segment, sin_segment, arc, left_legend
        )

        # --------------------------- RIGHT: GRAPHS ----------------------------
        right_axes = Axes(
            x_range=[X_MIN, X_MAX, np.pi / 2],
            y_range=[-1.2, 1.2, 0.5],
            x_length=7.2,
            y_length=4.6,
            x_axis_config={"include_numbers": False},
            y_axis_config={"include_numbers": True},
            axis_config=dict(include_tip=False, stroke_color=GRAY_B, stroke_width=3),
        )
        x_lab = right_axes.get_x_axis_label(MathTex("\\theta").set_color(WHITE))
        y_lab = right_axes.get_y_axis_label(
            MathTex("\\text{value}").set_color(WHITE), edge=LEFT, direction=LEFT, buff=0.5
        )

        pi_ticks = [
            (0, "0"),
            (np.pi / 2, "\\tfrac{\\pi}{2}"),
            (np.pi, "\\pi"),
            (3 * np.pi / 2, "\\tfrac{3\\pi}{2}"),
            (2 * np.pi, "2\\pi"),
        ]
        pi_labels = VGroup(
            *[
                MathTex(tex).scale(0.6).set_color(WHITE).next_to(right_axes.c2p(val, 0), DOWN, buff=0.15)
                for val, tex in pi_ticks
            ]
        )

        sin_full = right_axes.plot(lambda t: np.sin(t), x_range=[X_MIN, X_MAX], color=SIN_COLOR, stroke_opacity=0.25)
        cos_full = right_axes.plot(lambda t: np.cos(t), x_range=[X_MIN, X_MAX], color=COS_COLOR, stroke_opacity=0.25)

        sin_prog = always_redraw(
            lambda: right_axes.plot(
                lambda t: np.sin(t),
                x_range=[0, max(1e-4, min(theta.get_value(), X_MAX))],
                color=SIN_COLOR,
                stroke_width=6,
            )
        )
        cos_prog = always_redraw(
            lambda: right_axes.plot(
                lambda t: np.cos(t),
                x_range=[0, max(1e-4, min(theta.get_value(), X_MAX))],
                color=COS_COLOR,
                stroke_width=6,
            )
        )

        sin_dot = always_redraw(
            lambda: Dot(right_axes.c2p(theta.get_value(), np.sin(theta.get_value())), color=SIN_COLOR).scale(0.7)
        )
        cos_dot = always_redraw(
            lambda: Dot(right_axes.c2p(theta.get_value(), np.cos(theta.get_value())), color=COS_COLOR).scale(0.7)
        )
        v_line = always_redraw(
            lambda: DashedLine(
                right_axes.c2p(theta.get_value(), -1.2),
                right_axes.c2p(theta.get_value(), 1.2),
                color=THETA_COLOR,
                dash_length=0.1,
                dashed_ratio=0.6,
            )
        )

        legend = (
            VGroup(
                VGroup(Line(color=SIN_COLOR), MathTex("\\sin\\theta").scale(0.8).set_color(WHITE)).arrange(
                    RIGHT, buff=0.15
                ),
                VGroup(Line(color=COS_COLOR), MathTex("\\cos\\theta").scale(0.8).set_color(WHITE)).arrange(
                    RIGHT, buff=0.15
                ),
            )
            .arrange(RIGHT, buff=0.6)
            .next_to(right_axes, UP, buff=0.25)
        )

        right_panel = VGroup(
            right_axes,
            x_lab,
            y_lab,
            pi_labels,
            sin_full,
            cos_full,
            sin_prog,
            cos_prog,
            sin_dot,
            cos_dot,
            v_line,
            legend,
        )

        # ----------------------------- LAYOUT ---------------------------------
        layout = VGroup(left_panel, right_panel).arrange(RIGHT, buff=0.9, aligned_edge=DOWN)
        # Align vertical position of y=0 across panels
        y0_left, y0_right = left_axes.c2p(0, 0)[1], right_axes.c2p(0, 0)[1]
        right_panel.shift(UP * (y0_left - y0_right))

        margin_x, margin_y = 0.6, 0.4
        max_w = config.frame_width - 2 * margin_x
        max_h = config.frame_height - 2 * margin_y
        layout.scale(min(max_w / layout.width, max_h / layout.height, 1.0)).move_to(ORIGIN)

        # ------------------------- DRAW & ANIMATE -----------------------------
        self.add(layout)
        self.play(Create(left_axes), Create(unit_circle), run_time=0.8)
        self.play(Create(right_axes), FadeIn(x_lab), FadeIn(y_lab), FadeIn(pi_labels), run_time=0.8)
        self.play(FadeIn(sin_full), FadeIn(cos_full), run_time=0.6)

        self.add(OP, P_dot, v_drop, h_drop, cos_segment, sin_segment, arc, left_legend)
        self.add(sin_prog, cos_prog, sin_dot, cos_dot, v_line, legend)

        self.play(theta.animate.set_value(TAU), run_time=8.0, rate_func=linear)
        self.wait(0.8)
