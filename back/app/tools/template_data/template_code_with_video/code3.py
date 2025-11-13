from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        # ===== 例：f(x)=0.5x^2+1, 区間 [a,b]=[0,3] =====
        a, b = 0.0, 3.0
        def f(x): return 0.5*x*x + 1.0

        # ===== 右：座標軸（右半分サイズ想定）=====
        X_MIN, X_MAX, X_STEP = -0.3, 3.3, 0.5
        Y_MIN, Y_MAX, Y_STEP = 0.0, 6.3, 1.0
        AX_W, AX_H = 6.4, 4.2

        axes = Axes(
            x_range=[X_MIN, X_MAX, X_STEP],
            y_range=[Y_MIN, Y_MAX, Y_STEP],
            x_length=AX_W, y_length=AX_H,
            axis_config=dict(include_numbers=True, include_tip=False),
        )
        axes.x_axis.set_stroke(width=3)
        x_lab = axes.get_x_axis_label(MathTex("x"))
        y_lab = axes.get_y_axis_label(MathTex("y"), edge=LEFT, direction=LEFT, buff=0.4)
        axes_labels = VGroup(x_lab, y_lab)

        # 曲線と区間の目印
        graph = axes.plot(lambda x: f(x), x_range=[a, b], color=YELLOW)
        a_line = DashedLine(axes.c2p(a, 0), axes.c2p(a, f(a)), color=GRAY, dash_length=0.1, dashed_ratio=0.6)
        b_line = DashedLine(axes.c2p(b, 0), axes.c2p(b, f(b)), color=GRAY, dash_length=0.1, dashed_ratio=0.6)
        a_tex  = MathTex("a").scale(0.8).next_to(axes.c2p(a, 0), DOWN, buff=0.1)
        b_tex  = MathTex("b").scale(0.8).next_to(axes.c2p(b, 0), DOWN, buff=0.1)

        # ===== リーマン長方形（中点法） =====
        n_tracker = ValueTracker(3)        # 長方形の本数（表示はしない）
        use_midpoint = True
        RECT_COLOR = BLUE_B

        def make_rects(n_int: int):
            n_int = max(1, int(n_int))
            dx = (b - a) / n_int
            rects = VGroup()
            for i in range(n_int):
                xL = a + i*dx
                xR = xL + dx
                x_star = (xL + xR)/2 if use_midpoint else xL
                h = f(x_star)
                rects.add(Polygon(
                    axes.c2p(xL, 0),
                    axes.c2p(xL, h),
                    axes.c2p(xR, h),
                    axes.c2p(xR, 0),
                    color=RECT_COLOR,
                    fill_color=RECT_COLOR,
                    fill_opacity=0.50,
                    stroke_width=1.2,
                    stroke_opacity=0.9,
                ))
            return rects

        rects_mob = always_redraw(lambda: make_rects(n_tracker.get_value()))

        # 最終：青い面（チカチカ抑制用に置換）
        blue_area = axes.get_area(graph, x_range=(a, b), color=RECT_COLOR, opacity=0.55)
        blue_area.set_fill(opacity=0).set_stroke(opacity=0)   # 最初は非表示

        # ===== 左：最小限の数式（リーマン和→積分） =====
        title = Text("積分の意味").scale(0.66)
        sum_tex = MathTex(r"S_n=\sum_{i=1}^{n} f(x_i^{*})\,\Delta x").scale(1.0)
        eq_tex  = MathTex(r"\displaystyle \int_a^b f(x)\,dx=\lim_{n\to\infty}S_n").scale(1.0)
        left_col = VGroup(title, sum_tex, eq_tex).arrange(DOWN, aligned_edge=LEFT, buff=0.28)

        # ===== 右：n 表示（グラフの上に固定表示）=====
        n_text = MathTex("n=").scale(0.9)
        n_value = Integer(int(n_tracker.get_value())).scale(0.9)
        n_row = VGroup(n_text, n_value).arrange(RIGHT, buff=0.06)
        # 値の更新
        n_value.add_updater(lambda m: m.set_value(max(1, int(n_tracker.get_value()))))
        # 位置の更新（常に座標軸の上）
        n_row.add_updater(lambda m: m.next_to(axes, UP, buff=0.15))

        # ===== 右まとめ =====
        right_col = VGroup(axes, axes_labels, graph, a_line, b_line, a_tex, b_tex, rects_mob, blue_area, n_row)

        # ===== レイアウト：右は画面の約半分、左はコンパクト =====
        column_gap = 0.8
        margin_x, margin_y = 0.6, 0.4
        target_right_width = (config.frame_width - 2*margin_x - column_gap) * 0.5
        right_col.scale(target_right_width / right_col.width)
        layout = VGroup(left_col, right_col).arrange(RIGHT, buff=column_gap, aligned_edge=DOWN)

        max_w = config.frame_width  - 2*margin_x
        max_h = config.frame_height - 2*margin_y
        layout.scale(min(max_w/layout.width, max_h/layout.height, 1.0)).move_to(ORIGIN)

        # ===== 描画 =====
        self.add(layout)
        self.play(Create(axes), FadeIn(axes_labels), run_time=0.8)
        self.play(Create(graph), run_time=0.8)
        self.play(FadeIn(a_line), FadeIn(b_line), FadeIn(a_tex), FadeIn(b_tex), run_time=0.5)
        self.add(rects_mob, n_row)
        self.wait(0.3)

        # ===== アニメーション：粗い → 中くらい → 細かい（ここまで長方形）=====
        self.play(n_tracker.animate.set_value(18), run_time=1.6, rate_func=smooth)
        self.play(n_tracker.animate.set_value(36), run_time=1.8, rate_func=smooth)

        # ===== 切替：長方形 → 青い面、n を ∞ に =====
        # 変形の前にアップデータを止める（Transform の邪魔をしないため）
        n_value.clear_updaters()
        n_row.clear_updaters()
        infinity_row = VGroup(MathTex("n=").scale(0.9), MathTex("\\infty").scale(0.9)).arrange(RIGHT, buff=0.06)
        infinity_row.next_to(axes, UP, buff=0.15)

        self.play(
            FadeOut(rects_mob, run_time=0.7),
            blue_area.animate.set_fill(opacity=0.55).set_stroke(opacity=0.0),
        )
        self.play(Transform(n_row, infinity_row), run_time=0.6)
        self.wait(0.6)

        # 仕上げ：式を軽く強調（リーマン和→積分）
        self.play(Indicate(sum_tex), run_time=0.8)
        self.play(Indicate(eq_tex), run_time=0.8)
        self.wait(0.6)