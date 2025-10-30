# -----------------------------------------------------------------------------
# PURPOSE
#   Point P moves A->B->C->D at 1 cm/s across rectangle edges. Left: geometry.
#   Right: area(△ADP) vs time with guide lines and a prefix curve.
#
# 0.19-SAFE NOTES
#   - Background via self.camera.background_color
#   - Axes without tips; text colors tuned for black bg
# -----------------------------------------------------------------------------

from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # ---------------------------- CONFIG ----------------------------------
        AB = 4.0        # vertical size (A->B)
        AD = 8.0        # horizontal size (A->D)
        SPEED = 1.0     # cm/s
        PATH_LEN = AB + AD + AB   # 16 cm
        T_END = PATH_LEN / SPEED  # 16 s

        # ----------------- LEFT: RECTANGLE + MOVING POINT ---------------------
        left_axes = Axes(
            x_range=[0, AD, 2],
            y_range=[0, AB, 1],
            x_length=6.4, y_length=3.2,
            axis_config=dict(include_numbers=False, include_ticks=False,
                             include_tip=False, stroke_opacity=0.0),
        )

        rect_border = Rectangle(
            width=left_axes.x_length, height=left_axes.y_length,
            stroke_color=WHITE, stroke_width=3,
        ).move_to(left_axes.c2p(AD/2, AB/2))

        A_xy, B_xy, C_xy, D_xy = (0, 0), (0, AB), (AD, AB), (AD, 0)

        label_A = MathTex("A").scale(0.8).set_color(WHITE).next_to(left_axes.c2p(*A_xy), DOWN+LEFT,  buff=0.08)
        label_B = MathTex("B").scale(0.8).set_color(WHITE).next_to(left_axes.c2p(*B_xy), UP+LEFT,    buff=0.08)
        label_C = MathTex("C").scale(0.8).set_color(WHITE).next_to(left_axes.c2p(*C_xy), UP+RIGHT,   buff=0.08)
        label_D = MathTex("D").scale(0.8).set_color(WHITE).next_to(left_axes.c2p(*D_xy), DOWN+RIGHT, buff=0.08)

        AD_edge = Line(left_axes.c2p(*A_xy), left_axes.c2p(*D_xy), color=BLUE_E, stroke_width=5)

        ab_mid_anchor = VectorizedPoint(left_axes.c2p(0, AB/2))
        ad_mid_anchor = VectorizedPoint(left_axes.c2p(AD/2, 0))
        len_AB = MathTex("4\\,\\mathrm{cm}").scale(0.8).set_color(WHITE).next_to(ab_mid_anchor, LEFT,  buff=0.25)
        len_AD = MathTex("8\\,\\mathrm{cm}").scale(0.8).set_color(WHITE).next_to(ad_mid_anchor, DOWN,  buff=0.22)

        left_panel = VGroup(
            left_axes, rect_border, AD_edge,
            label_A, label_B, label_C, label_D, len_AB, len_AD
        )

        # ------------------- RIGHT: AREA-vs-TIME PLOT -------------------------
        right_axes = Axes(
            x_range=[0, T_END, 4],                 # 0–16 s
            y_range=[0, 0.5 * AD * AB, 4],         # 0–16 cm^2
            x_length=7.0, y_length=4.6,
            axis_config=dict(include_numbers=True, include_tip=False, stroke_color=GRAY_B, stroke_width=3),
        )
        x_label = right_axes.get_x_axis_label(MathTex("t\\,(\\mathrm{s})").set_color(WHITE))
        y_label = right_axes.get_y_axis_label(MathTex("\\mathrm{Area}\\,(\\mathrm{cm}^2)").set_color(WHITE),
                                              edge=LEFT, direction=LEFT, buff=0.6)
        right_panel = VGroup(right_axes, x_label, y_label)

        # ----------------------------- LAYOUT ---------------------------------
        layout = VGroup(left_panel, right_panel).arrange(RIGHT, buff=0.9, aligned_edge=DOWN)
        max_w = config.frame_width - 1.0
        if layout.width > max_w:
            layout.set_width(max_w)
        layout.to_edge(LEFT, buff=0.7)

        # ----------------------------- MODEL ----------------------------------
        t = ValueTracker(0.0)  # seconds

        def P_of_t(t_sec: float) -> tuple[float, float]:
            """Parametric motion along A->B->C->D at 1 cm/s."""
            u = SPEED * t_sec
            if u <= AB:                 return (0.0, u)           # A -> B
            if u <= AB + AD:            return (u - AB, AB)       # B -> C
            return (AD, 2 * AB + AD - u)                           # C -> D

        def area_ADP(t_sec: float) -> float:
            """Area of triangle △ADP with base AD on the x-axis."""
            _, y = P_of_t(t_sec)
            return 0.5 * AD * y

        P_dot = always_redraw(lambda: Dot(left_axes.c2p(*P_of_t(t.get_value())), color=YELLOW).scale(0.7))
        P_label = always_redraw(lambda: MathTex("P").scale(0.7).set_color(WHITE).next_to(
            left_axes.c2p(*P_of_t(t.get_value())), UR, buff=0.08
        ))
        tri_ADP = always_redraw(lambda: Polygon(
            left_axes.c2p(*A_xy), left_axes.c2p(*D_xy), left_axes.c2p(*P_of_t(t.get_value())),
            color=PINK, fill_color=PINK, fill_opacity=0.6, stroke_width=2,
        ).set_z_index(-1))

        area_value = DecimalNumber(0, num_decimal_places=2).scale(0.9).set_color(WHITE)
        area_label = VGroup(MathTex("\\mathrm{Area}(\\triangle ADP)=").scale(0.9).set_color(WHITE), area_value)\
                        .arrange(RIGHT, buff=0.08)
        area_label.next_to(left_panel, UP, buff=0.25).align_to(left_panel, LEFT)
        area_value.add_updater(lambda m: m.set_value(area_ADP(t.get_value())))

        full_curve = right_axes.plot(lambda tau: area_ADP(tau), x_range=[0, T_END],
                                     use_smoothing=False, color=GRAY_B, stroke_opacity=0.25)

        prog_curve = always_redraw(lambda:
            right_axes.plot(lambda tau: area_ADP(tau),
                            x_range=[0, max(1e-6, min(t.get_value(), T_END))],
                            use_smoothing=False, color=YELLOW, stroke_width=6)
        )
        moving_dot = always_redraw(lambda:
            Dot(right_axes.c2p(t.get_value(), area_ADP(t.get_value())), color=YELLOW).scale(0.7)
        )
        v_line = always_redraw(lambda:
            DashedLine(right_axes.c2p(t.get_value(), 0),
                       right_axes.c2p(t.get_value(), area_ADP(t.get_value())),
                       color=YELLOW, dash_length=0.12, dashed_ratio=0.6, stroke_width=2)
        )
        h_line = always_redraw(lambda:
            DashedLine(right_axes.c2p(0, area_ADP(t.get_value())),
                       right_axes.c2p(t.get_value(), area_ADP(t.get_value())),
                       color=YELLOW, dash_length=0.12, dashed_ratio=0.6, stroke_width=2)
        )

        t_num = DecimalNumber(0, num_decimal_places=2).scale(0.9).set_color(WHITE)
        t_label = VGroup(MathTex("t=").scale(0.9).set_color(WHITE), t_num).arrange(RIGHT, buff=0.06)
        t_label.next_to(right_panel, UP, buff=0.25).align_to(right_panel, RIGHT)
        t_num.add_updater(lambda m: m.set_value(t.get_value()))

        # ------------------------- DRAW & ANIMATE -----------------------------
        self.add(
            left_axes, rect_border, AD_edge, tri_ADP, P_dot, P_label,
            label_A, label_B, label_C, label_D, len_AB, len_AD,
            area_label, right_axes, x_label, y_label,
            full_curve, prog_curve, moving_dot, v_line, h_line, t_label
        )

        self.play(t.animate.set_value(T_END), run_time=T_END, rate_func=linear)
        self.wait(0.6)
