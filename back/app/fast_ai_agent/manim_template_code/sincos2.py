# -----------------------------------------------------------------------------
# PURPOSE
#   θ from 0° to 360° in 30° steps. Left: unit circle + right triangle marker.
#   Right: text readouts (θ, sinθ, cosθ) updated with TransformMatchingTex.
#
# 0.18.1 NOTES
#   - Radians internally, degrees for labels via np.deg2rad/np.degrees
#   - Background via self.camera.background_color (BLACK)
# -----------------------------------------------------------------------------

from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        # ---------------------------- CONFIG ----------------------------------
        SIN_COLOR, COS_COLOR, THETA_COLOR = RED, BLUE, YELLOW
        theta = ValueTracker(0.0)  # radians

        # --------------------------- LEFT PANEL -------------------------------
        left_axes = Axes(
            x_range=[-1.2, 1.2, 0.5],
            y_range=[-1.2, 1.2, 0.5],
            x_length=5.0,
            y_length=5.0,
            axis_config=dict(include_numbers=False, include_tip=False, stroke_color=GRAY_B, stroke_width=3),
        )
        unit_circle = ParametricFunction(
            lambda t: left_axes.c2p(np.cos(t), np.sin(t)), t_range=[0, TAU], color=WHITE, stroke_width=3
        )

        def P_xy() -> tuple[float, float]:
            t = theta.get_value()
            return (np.cos(t), np.sin(t))

        OP = always_redraw(lambda: Line(left_axes.c2p(0, 0), left_axes.c2p(*P_xy()), color=THETA_COLOR, stroke_width=4))
        P_dot = always_redraw(lambda: Dot(left_axes.c2p(*P_xy()), color=WHITE).scale(0.75))

        cos_seg = always_redraw(
            lambda: Line(
                left_axes.c2p(0, 0), left_axes.c2p(np.cos(theta.get_value()), 0), color=COS_COLOR, stroke_width=6
            )
        )
        sin_seg = always_redraw(
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

        legend = (
            VGroup(
                MathTex(r"\sin\theta").scale(0.8).set_color(SIN_COLOR),
                MathTex(r"\cos\theta").scale(0.8).set_color(COS_COLOR),
            )
            .arrange(RIGHT, buff=0.6)
            .next_to(left_axes, UP, buff=0.25)
        )

        # -------------------------- RIGHT PANEL (TEXT) ------------------------
        cos_label = MathTex(r"\cos\theta \;=").scale(0.9).set_color(WHITE)
        sin_label = MathTex(r"\sin\theta \;=").scale(0.9).set_color(WHITE)
        cos_val_tex = MathTex("1").scale(0.9).set_color(COS_COLOR)  # θ=0°
        sin_val_tex = MathTex("0").scale(0.9).set_color(SIN_COLOR)
        cos_row = VGroup(cos_label, cos_val_tex).arrange(RIGHT, buff=0.08)
        sin_row = VGroup(sin_label, sin_val_tex).arrange(RIGHT, buff=0.08)
        values_group = VGroup(cos_row, sin_row).arrange(DOWN, aligned_edge=LEFT, buff=0.35)

        theta_tex = MathTex(r"\Theta \;=\; 0^{\circ}").scale(0.9).set_color(WHITE)
        theta_tex.next_to(values_group, UP, buff=0.35).align_to(values_group, LEFT)

        left_panel = VGroup(left_axes, unit_circle, OP, P_dot, v_drop, h_drop, cos_seg, sin_seg, legend)
        right_panel = VGroup(theta_tex, values_group)

        # ------------------------------ LAYOUT --------------------------------
        layout = VGroup(left_panel, right_panel).arrange(RIGHT, buff=1.0, aligned_edge=DOWN)
        margin = 0.5
        if layout.width > (config.frame_width - 2 * margin):
            layout.set_width(config.frame_width - 2 * margin)
        layout.move_to(ORIGIN)

        self.add(layout)
        self.play(Create(left_axes), Create(unit_circle), run_time=0.8)
        self.play(FadeIn(legend), run_time=0.4)
        self.add(OP, P_dot, v_drop, h_drop, cos_seg, sin_seg)
        self.add(right_panel)

        # -------------------- DATA TABLES & HELPERS ---------------------------
        cos_map = {
            0: "1",
            30: r"\tfrac{\sqrt{3}}{2}",
            60: r"\tfrac{1}{2}",
            90: "0",
            120: r"-\tfrac{1}{2}",
            150: r"-\tfrac{\sqrt{3}}{2}",
            180: r"-1",
            210: r"-\tfrac{\sqrt{3}}{2}",
            240: r"-\tfrac{1}{2}",
            270: "0",
            300: r"\tfrac{1}{2}",
            330: r"\tfrac{\sqrt{3}}{2}",
            360: "1",
        }
        sin_map = {
            0: "0",
            30: r"\tfrac{1}{2}",
            60: r"\tfrac{\sqrt{3}}{2}",
            90: "1",
            120: r"\tfrac{\sqrt{3}}{2}",
            150: r"\tfrac{1}{2}",
            180: "0",
            210: r"-\tfrac{1}{2}",
            240: r"-\tfrac{\sqrt{3}}{2}",
            270: r"-1",
            300: r"-\tfrac{\sqrt{3}}{2}",
            330: r"-\tfrac{1}{2}",
            360: "0",
        }

        def acute_deg(d: int) -> int | None:
            """Return 30 or 60 for an angle d (mod 180), None for multiples of 90."""
            m = d % 180
            if m in (0, 90):
                return None
            return m if m < 90 else 180 - m

        def triangle_with_interior_right_mark() -> VGroup:
            """Right triangle O-E-P with a small interior right-angle corner at E."""
            d = int(np.round(np.degrees(theta.get_value()))) % 360
            if acute_deg(d) is None:
                return VGroup()

            O = left_axes.c2p(0, 0)
            E = left_axes.c2p(np.cos(theta.get_value()), 0)
            P = left_axes.c2p(np.cos(theta.get_value()), np.sin(theta.get_value()))

            tri = Polygon(O, E, P, stroke_color=WHITE, stroke_width=2, fill_color=PURPLE, fill_opacity=0.22)

            u_EO, u_EP = O - E, P - E
            if np.linalg.norm(u_EO) > 1e-9:
                u_EO = u_EO / np.linalg.norm(u_EO)
            if np.linalg.norm(u_EP) > 1e-9:
                u_EP = u_EP / np.linalg.norm(u_EP)
            s = 0.18
            A1, A2 = E + s * u_EO, E + s * u_EP
            A12 = E + s * u_EO + s * u_EP
            corner = VGroup(Line(A1, A12, color=WHITE, stroke_width=2), Line(A2, A12, color=WHITE, stroke_width=2))
            return VGroup(tri, corner)

        def angle_arc_and_label_smallest() -> VGroup:
            """Draw the smaller angle at O between OE (blue) and OP (yellow), label 30°/60°."""
            d = int(np.round(np.degrees(theta.get_value()))) % 360
            a = acute_deg(d)
            if a is None:
                return VGroup()

            O = left_axes.c2p(0, 0)
            E = left_axes.c2p(np.cos(theta.get_value()), 0)
            P = left_axes.c2p(np.cos(theta.get_value()), np.sin(theta.get_value()))
            base, ray = Line(O, E), Line(O, P)

            argE = 0.0 if np.cos(theta.get_value()) >= 0 else np.pi
            argP = np.arctan2(np.sin(theta.get_value()), np.cos(theta.get_value()))
            use_other = ((argP - argE) % (2 * np.pi)) > np.pi

            arc_radius = 0.36
            ang = Angle(base, ray, radius=arc_radius, other_angle=use_other, color=THETA_COLOR, stroke_width=4)

            u_OE, u_OP = E - O, P - O
            if np.linalg.norm(u_OE) > 1e-9:
                u_OE = u_OE / np.linalg.norm(u_OE)
            if np.linalg.norm(u_OP) > 1e-9:
                u_OP = u_OP / np.linalg.norm(u_OP)
            bis = u_OE + u_OP
            if np.linalg.norm(bis) > 1e-9:
                bis = bis / np.linalg.norm(bis)

            label = MathTex(rf"{a}^{{\circ}}").scale(0.5).set_color(WHITE)
            label.move_to(O + (arc_radius + 0.30) * bis)
            return VGroup(ang, label)

        tri_group = always_redraw(triangle_with_interior_right_mark)
        angle_deco = always_redraw(angle_arc_and_label_smallest)
        self.add(tri_group, angle_deco)

        # ------------------------ STEP THROUGH ANGLES -------------------------
        angles = list(range(0, 361, 30))

        def update_values_panel(d: int):
            """Update θ, cosθ, sinθ text with soft matching transforms."""
            nonlocal theta_tex, cos_val_tex, sin_val_tex
            new_theta_tex = MathTex(rf"\Theta \;=\; {d}^{{\circ}}").scale(0.9).set_color(WHITE)
            new_theta_tex.next_to(values_group, UP, buff=0.35).align_to(values_group, LEFT)
            self.play(TransformMatchingTex(theta_tex, new_theta_tex), run_time=0.25)
            theta_tex = new_theta_tex

            new_cos = MathTex(cos_map[d]).scale(0.9).set_color(COS_COLOR).next_to(cos_label, RIGHT, buff=0.08)
            new_sin = MathTex(sin_map[d]).scale(0.9).set_color(SIN_COLOR).next_to(sin_label, RIGHT, buff=0.08)
            self.play(
                TransformMatchingTex(cos_val_tex, new_cos), TransformMatchingTex(sin_val_tex, new_sin), run_time=0.25
            )
            cos_val_tex, sin_val_tex = new_cos, new_sin

        for d in angles:
            self.play(theta.animate.set_value(np.deg2rad(d)), run_time=0.6, rate_func=smooth)
            update_values_panel(d)
            self.wait(0.8)

        self.wait(0.6)
