from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        # ===== 軸と放物線の設計 =====
        # 放物線: y = x^2 + c（a=1, b=0）。c を 2→0→-3 と動かしても必ず枠内に収まるレンジ。
        X_MIN, X_MAX, X_STEP = -3, 3, 1
        Y_MIN, Y_MAX, Y_STEP = -6, 14, 2

        # 右グラフの見た目サイズ（後で右半分にスケール調整するが、基準サイズはやや小さめに）
        AX_X_LEN, AX_Y_LEN = 6.0, 4.2

        # ===== 左カラム（説明） =====
        title = Text("二次関数：判別式 D と x 軸との交点").scale(0.62)

        formula = MathTex("y=ax^2+bx+c\\quad (a\\ne 0)").scale(0.9)
        disc    = MathTex("D=b^2-4ac").scale(0.9)
        quad    = MathTex("x=\\frac{-b\\pm\\sqrt{D}}{2a}").scale(0.9)
        left_formula_grp = VGroup(formula, disc, quad).arrange(DOWN, aligned_edge=LEFT, buff=0.16)

        # a,b は固定表示、c は可変表示（D の上に配置）
        a_val, b_val = 1.0, 0.0
        c_tracker = ValueTracker(2.0)  # 初期 c=2（D<0）

        c_num = DecimalNumber(c_tracker.get_value(), num_decimal_places=2).scale(0.9)
        param_row = VGroup(
            MathTex("a=1,").scale(0.9),
            MathTex("\\;b=0,").scale(0.9),
            VGroup(MathTex("\\;c=").scale(0.9), c_num).arrange(RIGHT, buff=0.06),
        ).arrange(RIGHT, buff=0.14)

        # D の表示（param_row の直下）
        D_num = DecimalNumber(0.0, num_decimal_places=2).scale(0.9)
        D_label = VGroup(MathTex("D\\;=").scale(0.9), D_num).arrange(RIGHT, buff=0.08)

        # 説明（ケース表示）は一番下に配置（のちほど右グラフの下端と揃える）
        case_box  = RoundedRectangle(corner_radius=0.15, width=5.4, height=0.9, color=WHITE).set_fill(opacity=0.08)
        case_text = Text("D < 0  →  交点なし").scale(0.56).set_color(RED).move_to(case_box.get_center())
        case_panel = VGroup(case_box, case_text)

        # 左カラムの「上側説明」だけをまとめる（重なり防止のためケースは別グループ）
        left_top = VGroup(title, left_formula_grp, param_row, D_label).arrange(
            DOWN, aligned_edge=LEFT, buff=0.22
        )

        # ===== 右カラム（座標軸と放物線） =====
        axes = Axes(
            x_range=[X_MIN, X_MAX, X_STEP],
            y_range=[Y_MIN, Y_MAX, Y_STEP],
            x_length=AX_X_LEN,
            y_length=AX_Y_LEN,
            axis_config=dict(include_numbers=True, include_tip=False),
        )
        axes.x_axis.set_stroke(width=3)

        a, b = a_val, b_val
        eps = 1e-6

        def f(x):
            c = c_tracker.get_value()
            return a*x*x + b*x + c

        graph = always_redraw(lambda: axes.plot(lambda x: f(x), x_range=[X_MIN, X_MAX], color=YELLOW))

        # 交点の可視化（D の符号で 0/1/2 個、範囲外は非表示）
        def roots_group():
            c = c_tracker.get_value()
            D = b*b - 4*a*c
            g = VGroup()
            if D > eps:
                r = np.sqrt(D)
                x1 = (-b - r) / (2*a)
                x2 = (-b + r) / (2*a)
                if X_MIN <= x1 <= X_MAX:
                    d1 = Dot(axes.c2p(x1, 0), color=GREEN).scale(0.8)
                    l1 = DashedLine(axes.c2p(x1, 0), axes.c2p(x1, f(x1)), color=GREEN, dash_length=0.12, dashed_ratio=0.6)
                    x1_label = MathTex("x_1").scale(0.72).next_to(d1, DOWN, buff=0.06)
                    g.add(l1, d1, x1_label)
                if X_MIN <= x2 <= X_MAX:
                    d2 = Dot(axes.c2p(x2, 0), color=GREEN).scale(0.8)
                    l2 = DashedLine(axes.c2p(x2, 0), axes.c2p(x2, f(x2)), color=GREEN, dash_length=0.12, dashed_ratio=0.6)
                    x2_label = MathTex("x_2").scale(0.72).next_to(d2, DOWN, buff=0.06)
                    g.add(l2, d2, x2_label)
            elif abs(D) <= eps:
                x0 = -b / (2*a)
                if X_MIN <= x0 <= X_MAX:
                    d0 = Dot(axes.c2p(x0, 0), color=ORANGE).scale(0.9)
                    x0_label = MathTex("x_0").scale(0.72).next_to(d0, DOWN, buff=0.06)
                    g.add(d0, x0_label)
            return g

        roots = always_redraw(roots_group)
        right_col = VGroup(axes, graph, roots)  # 重ね描き（arrangeしない）

        # ===== レイアウト：右半分はグラフ、左は説明 =====
        margin_x, margin_y = 0.6, 0.4
        column_gap = 0.8

        # 右カラムを「画面の右半分」に拡大（横幅ターゲットを半分に設定）
        target_right_width = (config.frame_width - 2 * margin_x - column_gap) * 0.5
        # 一旦自然幅でスケールを決める
        scale_right = target_right_width / right_col.width
        right_col.scale(scale_right)

        # 左は「上の説明」と「下のケース」を縦に（ケースが最下段）
        left_col = VGroup(left_top, case_panel).arrange(DOWN, aligned_edge=LEFT, buff=0.24)

        # 左右を下端で揃えて横並び（ケースの下端と座標軸の下端が一致）
        layout = VGroup(left_col, right_col).arrange(RIGHT, buff=column_gap, aligned_edge=DOWN)

        # 画面内に収まるように最終フィット（上下・左右ともに）
        max_w = config.frame_width  - 2 * margin_x
        max_h = config.frame_height - 2 * margin_y
        scale_all = min(max_w / layout.width, max_h / layout.height, 1.0)
        layout.scale(scale_all)
        layout.move_to(ORIGIN)

        # ===== Updaters（c と D を同時更新）=====
        def update_D_and_c(_m=None):
            c = c_tracker.get_value()
            D = b*b - 4*a*c
            c_num.set_value(c)
            D_num.set_value(D)
            if D > eps:
                D_num.set_color(GREEN)
            elif D < -eps:
                D_num.set_color(RED)
            else:
                D_num.set_color(YELLOW)

        c_num.add_updater(lambda m: update_D_and_c())
        D_num.add_updater(lambda m: update_D_and_c())

        # ===== 描画・アニメーション =====
        self.add(layout)
        self.play(Create(axes), run_time=1.0)
        self.play(Create(graph), run_time=1.0)
        self.add(roots)
        self.wait(0.4)

        # D = 0（接する）：ケース表示は一番下に固定されたまま
        self.play(c_tracker.animate.set_value(0.0), run_time=2.2, rate_func=linear)
        case_text_eq = Text("D = 0  →  接する（重解）").scale(0.56).set_color(YELLOW).move_to(case_box.get_center())
        self.play(Transform(case_text, case_text_eq), run_time=0.5)
        self.play(Indicate(roots, color=ORANGE), run_time=0.9)

        # D > 0（2点で交わる）
        self.play(c_tracker.animate.set_value(-3.0), run_time=2.2, rate_func=linear)
        case_text_gt = Text("D > 0  →  2点で交わる").scale(0.56).set_color(GREEN).move_to(case_box.get_center())
        self.play(Transform(case_text, case_text_gt), run_time=0.5)
        self.play(Flash(roots, color=GREEN), run_time=0.9)
        self.wait(0.6)