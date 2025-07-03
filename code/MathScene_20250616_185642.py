
from manim import *

class IntegrabilitySinOneOverX(Scene):
    def construct(self):
        # Title and introduction
        title = Tex("Integrability of $f(x) = \\sin(1/x)$ with Oscillation")
        title.scale(1.2)
        title.to_edge(UP)
        
        func_def = MathTex(
            r"f(x) = \begin{cases} \sin\left(\frac{1}{x}\right) & \text{if } x \in (0,1] \\ 1 & \text{if } x = 0 \end{cases}"
        )
        func_def.next_to(title, DOWN)
        
        self.play(Write(title))
        self.wait(1)
        self.play(Write(func_def))
        self.wait(2)
        
        # Create axes and function graph
        axes = Axes(
            x_range=[0, 1.2, 0.2],
            y_range=[-1.5, 1.5, 0.5],
            axis_config={"color": BLUE},
            tips=False,
        )
        axes.scale_to_fit_height(5)
        axes.to_edge(DOWN, buff=0.5)
        
        # Plot sin(1/x) avoiding x=0 singularity
        graph = axes.plot(
            lambda x: np.sin(1/x),
            x_range=[0.001, 1, 0.0001],
            use_smoothing=False,
            color=YELLOW
        )
        
        # Add point at (0,1)
        dot = Dot(axes.c2p(0, 1), color=GREEN)
        dot_label = MathTex(r"(0,1)").next_to(dot, UP, buff=0.1)
        
        # Oscillation indicator near zero
        oscillation_text = Tex("Infinite Oscillation", color=RED).scale(0.8)
        oscillation_text.next_to(axes.c2p(0.05, 0), UP)
        arrow = Arrow(
            oscillation_text.get_bottom(),
            axes.c2p(0.01, 0.5),
            color=RED,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15
        )
        
        self.play(Create(axes), Create(graph), run_time=2)
        self.play(FadeIn(dot), Write(dot_label))
        self.play(Write(oscillation_text), GrowArrow(arrow))
        self.wait(3)
        
        # Introduce epsilon and partition
        epsilon = 0.5
        delta = epsilon / 4
        
        epsilon_label = MathTex(r"\epsilon = 0.5", color=GREEN)
        delta_label = MathTex(r"\delta = \frac{\epsilon}{4} = 0.125", color=RED)
        group = VGroup(epsilon_label, delta_label).arrange(DOWN, aligned_edge=LEFT)
        group.to_edge(UR)
        
        self.play(Write(epsilon_label))
        self.wait(1)
        self.play(Write(delta_label))
        self.wait(2)
        
        # Show partition points
        partition_points = [0, delta, 1]
        vert_lines = VGroup()
        labels = VGroup()
        for i, x in enumerate(partition_points):
            line = DashedLine(
                axes.c2p(x, -1.5),
                axes.c2p(x, 1.5),
                color=RED if i==1 else BLUE,
                stroke_width=2
            )
            label = MathTex(f"{x:.3f}" if i==1 else str(x)).next_to(axes.c2p(x, 0), DOWN, buff=0.1)
            vert_lines.add(line)
            labels.add(label)
        
        self.play(
            Create(vert_lines),
            Write(labels),
            run_time=2
        )
        self.wait(2)
        
        # Highlight [0, δ] interval
        rect = Rectangle(
            width=axes.c2p(delta, 0)[0] - axes.c2p(0, 0)[0],
            height=axes.c2p(0, 1)[1] - axes.c2p(0, -1)[1],
            color=RED,
            fill_opacity=0.2,
            stroke_width=0
        )
        rect.move_to(axes.c2p(delta/2, 0))
        
        bound_text = MathTex(r"\sup |f| \leq 1", color=RED).next_to(rect, UP)
        area_bound = MathTex(
            r"\text{Area contribution} \leq (1 - (-1)) \cdot \delta = 2\delta = \frac{\epsilon}{2}",
            color=RED
        ).next_to(bound_text, DOWN)
        
        self.play(FadeIn(rect))
        self.play(Write(bound_text))
        self.wait(1)
        self.play(Write(area_bound))
        self.wait(3)
        
        # Refine partition in [δ, 1]
        refine_text = Tex("Refine partition in $[\\delta, 1]$ for uniform continuity", color=GREEN)
        refine_text.to_edge(UP)
        self.play(ReplacementTransform(title, refine_text))
        self.wait(2)
        
        n_points = 8
        refine_points = np.linspace(delta, 1, n_points)
        refine_lines = VGroup()
        for x in refine_points[1:-1]:
            line = DashedLine(
                axes.c2p(x, -1.5),
                axes.c2p(x, 1.5),
                color=GREEN,
                stroke_width=1.5,
                stroke_opacity=0.7
            )
            refine_lines.add(line)
        
        self.play(Create(refine_lines), run_time=2)
        self.wait(2)
        
        # Show small oscillation in subintervals
        sample_x = 0.3
        sample_interval = Rectangle(
            width=axes.c2p(0.05, 0)[0] - axes.c2p(0, 0)[0],
            height=axes.c2p(0, 0.2)[1] - axes.c2p(0, 0)[1],
            color=GREEN,
            fill_opacity=0.3,
            stroke_width=0
        )
        sample_interval.move_to(axes.c2p(sample_x + 0.025, 0))
        
        oscillation_bound = MathTex(
            r"\text{Small oscillation: } M_i - m_i < \frac{\epsilon}{2(1-\delta)}",
            color=GREEN
        ).next_to(sample_interval, UP, buff=0.5)
        
        self.play(FadeIn(sample_interval))
        self.play(Write(oscillation_bound))
        self.wait(2)
        
        # Total area bound
        total_bound = MathTex(
            r"U(f,P) - L(f,P) < \underbrace{\frac{\epsilon}{2}}_{\text{[0,\delta]}} + \underbrace{\frac{\epsilon}{2}}_{\text{[\delta,1]}} = \epsilon",
            color=YELLOW
        )
        total_bound.scale(0.9)
        total_bound.to_edge(UP)
        
        self.play(ReplacementTransform(refine_text, total_bound))
        self.wait(3)
        
        # Conclusion
        conclusion = Tex("Therefore, $f$ is Riemann integrable on $[0,1]$", color=GREEN)
        conclusion.scale(1.1)
        conclusion.to_edge(DOWN)
        
        self.play(Write(conclusion))
        self.wait(3)
        
        # Final fade out
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait()
