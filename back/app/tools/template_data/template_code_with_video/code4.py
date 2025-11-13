from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        # ===== 設定 =====
        AB = 4.0   # 縦（A->B）
        AD = 8.0   # 横（A->D）
        SPEED = 1.0  # cm/s（指定：1cm/s）
        PATH_LEN = AB + AD + AB   # A->B->C->D = 16 cm
        T_END = PATH_LEN / SPEED  # 16 s

        # ===== 左：長方形パネル（A左下, B左上, C右上, D右下）=====
        left_axes = Axes(
            x_range=[0, AD, 2],
            y_range=[0, AB, 1],
            x_length=6.4,   # 8:4 の比を保った可視サイズ
            y_length=3.2,
            axis_config=dict(include_numbers=False, include_ticks=False, include_tip=False, stroke_opacity=0.0),
        )

        rect_border = Rectangle(
            width=left_axes.x_length,
            height=left_axes.y_length,
            stroke_color=WHITE,
            stroke_width=3,
        ).move_to(left_axes.c2p(AD/2, AB/2))

        # 頂点（幾何座標）
        A_xy = (0, 0)
        B_xy = (0, AB)
        C_xy = (AD, AB)
        D_xy = (AD, 0)

        # 頂点ラベル
        label_A = MathTex("A").scale(0.8).next_to(left_axes.c2p(*A_xy), DOWN+LEFT,  buff=0.08)
        label_B = MathTex("B").scale(0.8).next_to(left_axes.c2p(*B_xy), UP+LEFT,    buff=0.08)
        label_C = MathTex("C").scale(0.8).next_to(left_axes.c2p(*C_xy), UP+RIGHT,   buff=0.08)
        label_D = MathTex("D").scale(0.8).next_to(left_axes.c2p(*D_xy), DOWN+RIGHT, buff=0.08)

        # 底辺 AD を強調（x軸上）
        AD_edge = Line(left_axes.c2p(*A_xy), left_axes.c2p(*D_xy), color=BLUE_E, stroke_width=5)

        # ------ 辺の長さ：AB左外側とAD下外側の2か所のみ ------
        ab_mid_anchor = VectorizedPoint(left_axes.c2p(0, AB/2))
        ad_mid_anchor = VectorizedPoint(left_axes.c2p(AD/2, 0))
        len_AB = MathTex("4\\,\\mathrm{cm}").scale(0.8)
        len_AD = MathTex("8\\,\\mathrm{cm}").scale(0.8)
        len_AB.next_to(ab_mid_anchor, LEFT,  buff=0.25)   # AB の左外側
        len_AD.next_to(ad_mid_anchor, DOWN,  buff=0.22)   # AD の下外側

        left_panel = VGroup(
            left_axes, rect_border, AD_edge,
            label_A, label_B, label_C, label_D,
            len_AB, len_AD
        )

        # ===== 右：グラフパネル（面積 vs 時間）=====
        right_axes = Axes(
            x_range=[0, T_END, 4],                 # 0～16 s
            y_range=[0, 0.5 * AD * AB, 4],         # 0～16 cm^2
            x_length=7.0,
            y_length=4.6,
            axis_config=dict(include_numbers=True, include_tip=False),
        )
        x_label = right_axes.get_x_axis_label(MathTex("t\\,(\\mathrm{s})"))
        y_label = right_axes.get_y_axis_label(MathTex("\\mathrm{Area}\\,(\\mathrm{cm}^2)"),
                                              edge=LEFT, direction=LEFT, buff=0.6)
        right_panel = VGroup(right_axes, x_label, y_label)

        # ===== レイアウト（外側ラベルも含めて幅調整→左端に余白を確保）=====
        layout = VGroup(left_panel, right_panel).arrange(RIGHT, buff=0.9, aligned_edge=DOWN)
        max_w = config.frame_width - 1.0  # 左右に余白
        if layout.width > max_w:
            layout.set_width(max_w)
        layout.to_edge(LEFT, buff=0.7)

        # ===== 時間トラッカー =====
        t = ValueTracker(0.0)  # 秒

        # ===== P(t) と 面積 S(t) =====
        # u = 進んだ距離[cm] = SPEED * t
        def P_of_t(t_sec: float):
            u = SPEED * t_sec
            if u <= AB:                 # A(0,0) -> B(0,AB)
                return (0.0, u)
            elif u <= AB + AD:          # B(0,AB) -> C(AD,AB)
                return (u - AB, AB)
            else:                        # C(AD,AB) -> D(AD,0) で終了
                return (AD, 2 * AB + AD - u)

        def area_ADP(t_sec: float) -> float:
            # A=(0,0), D=(AD,0) を底辺とする三角形の面積 = (AD/2) * y_P
            _, y = P_of_t(t_sec)
            return 0.5 * AD * y

        # ===== 左：動的オブジェクト =====
        P_dot = always_redraw(lambda: Dot(left_axes.c2p(*P_of_t(t.get_value())), color=YELLOW).scale(0.7))
        P_label = always_redraw(lambda: MathTex("P").scale(0.7).next_to(
            left_axes.c2p(*P_of_t(t.get_value())), UR, buff=0.08
        ))
        tri_ADP = always_redraw(lambda: Polygon(
            left_axes.c2p(*A_xy),
            left_axes.c2p(*D_xy),
            left_axes.c2p(*P_of_t(t.get_value())),
            color=PINK, fill_color=PINK, fill_opacity=0.6, stroke_width=2,
        ))
        tri_ADP.set_z_index(-1)

        # 面積の数値表示（単位は付けない）
        area_value = DecimalNumber(0, num_decimal_places=2).scale(0.9)
        area_label = VGroup(
            MathTex("\\mathrm{Area}(\\triangle ADP)=").scale(0.9),
            area_value,
        ).arrange(RIGHT, buff=0.08)
        area_label.next_to(left_panel, UP, buff=0.25).align_to(left_panel, LEFT)

        def update_area_value(m: DecimalNumber):
            m.set_value(area_ADP(t.get_value()))
        area_value.add_updater(update_area_value)

        # ===== 右：面積グラフ =====
        full_curve = right_axes.plot(
            lambda tau: area_ADP(tau),
            x_range=[0, T_END],
            use_smoothing=False,
            color=GRAY_B,
            stroke_opacity=0.25,
        )

        def partial_curve():
            t_now = t.get_value()
            t_eps = max(1e-6, min(t_now, T_END))
            return right_axes.plot(
                lambda tau: area_ADP(tau),
                x_range=[0, t_eps],
                use_smoothing=False,
                color=YELLOW,
                stroke_width=6,
            )
        prog_curve = always_redraw(partial_curve)

        moving_dot = always_redraw(lambda:
            Dot(right_axes.c2p(t.get_value(), area_ADP(t.get_value())), color=YELLOW).scale(0.7)
        )
        v_line = always_redraw(lambda:
            DashedLine(
                right_axes.c2p(t.get_value(), 0),
                right_axes.c2p(t.get_value(), area_ADP(t.get_value())),
                color=YELLOW, dash_length=0.12, dashed_ratio=0.6, stroke_width=2,
            )
        )
        h_line = always_redraw(lambda:
            DashedLine(
                right_axes.c2p(0, area_ADP(t.get_value())),
                right_axes.c2p(t.get_value(), area_ADP(t.get_value())),
                color=YELLOW, dash_length=0.12, dashed_ratio=0.6, stroke_width=2,
            )
        )

        # t の表示（単位 s は付けない）
        t_num = DecimalNumber(0, num_decimal_places=2).scale(0.9)
        t_label = VGroup(MathTex("t=").scale(0.9), t_num).arrange(RIGHT, buff=0.06)
        t_label.next_to(right_panel, UP, buff=0.25).align_to(right_panel, RIGHT)

        def update_t_num(m: DecimalNumber):
            m.set_value(t.get_value())
        t_num.add_updater(update_t_num)

        # ===== 描画・アニメーション =====
        self.add(
            left_axes, rect_border, AD_edge, tri_ADP, P_dot, P_label,
            label_A, label_B, label_C, label_D,
            len_AB, len_AD,
            area_label,
            right_axes, x_label, y_label, full_curve, prog_curve, moving_dot, v_line, h_line, t_label
        )
        # 等速 1cm/s で A->B->C->D まで（16秒）
        self.play(t.animate.set_value(T_END), run_time=T_END, rate_func=linear)
        self.wait(0.6)