from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        axes = Axes(
            x_range=[0, 360, 30],
            y_range=[-1.2, 1.2, 0.5],
            axis_config={"include_numbers": True, "include_tip": False, "stroke_color": GRAY_B}
        ).to_edge(RIGHT, buff=0.6)

        # 度→ラジアン
        def s(x):  return np.sin(np.deg2rad(x))
        def c(x):  return np.cos(np.deg2rad(x))
        def s2(x): return s(x)**2
        def c2(x): return c(x)**2
        def one(x): return 1.0

        # グラフ（先に生成しておく）
        g_s   = axes.plot(s,  x_range=[0, 360], color=GREEN)
        g_c   = axes.plot(c,  x_range=[0, 360], color=BLUE)
        g_s2  = axes.plot(s2, x_range=[0, 360], color=GREEN)
        g_c2  = axes.plot(c2, x_range=[0, 360], color=BLUE)
        g_sum = axes.plot(lambda x: s2(x) + c2(x), x_range=[0, 360], color=YELLOW)

        # y=1 を点線で
        g_one_solid  = axes.plot(one, x_range=[0, 360], color=TEAL, stroke_width=4)
        g_one        = DashedVMobject(g_one_solid, num_dashes=60, dashed_ratio=0.5)

        # タイトルと段階ラベル
        title = Text("sin・cos の二乗と恒等式  sin²x + cos²x = 1", font_size=30).to_edge(UP)
        lbl_step = Text("Step 1: sin x を表示", font_size=26).to_edge(UP).shift(DOWN*0.9)

        # 数式（日本語なしの MathTex）
        eq_final = MathTex(r"\sin^2 x + \cos^2 x = 1", font_size=42).to_edge(UP).shift(DOWN*0.4)

        # 進行
        self.play(FadeIn(title), Create(axes))

        # Step 1: sin x
        self.play(Write(lbl_step))
        self.play(Create(g_s), run_time=0.8)

        # Step 2: sin^2 x（sin を二乗へ変形）
        self.play(Transform(lbl_step, Text("Step 2: sin x を二乗 → sin^2 x", font_size=26).to_edge(UP).shift(DOWN*0.9)))
        self.play(Transform(g_s, g_s2), run_time=0.8)

        # Step 3: cos x
        self.play(Transform(lbl_step, Text("Step 3: cos x を表示", font_size=26).to_edge(UP).shift(DOWN*0.9)))
        self.play(Create(g_c), run_time=0.8)

        # Step 4: cos^2 x（cos を二乗へ変形）
        self.play(Transform(lbl_step, Text("Step 4: cos x を二乗 → cos^2 x", font_size=26).to_edge(UP).shift(DOWN*0.9)))
        self.play(Transform(g_c, g_c2), run_time=0.8)

        # Step 5: 和が常に 1
        self.play(Transform(lbl_step, Text("Step 5: sin^2 x + cos^2 x を表示（常に 1）", font_size=26).to_edge(UP).shift(DOWN*0.9)))
        self.play(Create(g_sum), Create(g_one), run_time=0.8)
        self.play(Write(eq_final))
        self.wait(1.0)
