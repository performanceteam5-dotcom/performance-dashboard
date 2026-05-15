import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Series,
  staticFile,
} from "remotion";
import { Audio } from "@remotion/media";

// ─── Design Tokens ───────────────────────────────────────────────
const C = {
  bg: "#0f1117",
  surface: "#1a1d27",
  surface2: "#242836",
  border: "#2d3348",
  text: "#e4e7f0",
  dim: "#8b91a8",
  accent: "#d4a574",
  accent2: "#7cb3c4",
  accent3: "#a8c97f",
  accent4: "#c49bd4",
};

// ─── Helpers ─────────────────────────────────────────────────────
function useSpring(frame: number, fps: number, delay = 0, damping = 200) {
  return spring({ frame: frame - delay, fps, config: { damping } });
}

function FadeSlide({
  children,
  from = 0,
  direction = "up",
}: {
  children: React.ReactNode;
  from?: number;
  direction?: "up" | "left" | "right";
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = useSpring(frame, fps, from);
  const opacity = interpolate(sp, [0, 1], [0, 1]);
  const offset = interpolate(sp, [0, 1], [direction === "up" ? 40 : direction === "left" ? -60 : 60, 0]);
  return (
    <div
      style={{
        opacity,
        transform: direction === "up"
          ? `translateY(${offset}px)`
          : `translateX(${offset}px)`,
      }}
    >
      {children}
    </div>
  );
}

// ─── Scene 1: Intro (0-3s = 90f) ─────────────────────────────────
function SceneIntro() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });
  const titleOp = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [20, 50], [30, 0], { extrapolateRight: "clamp" });
  const subOp = interpolate(frame, [40, 70], [0, 1], { extrapolateRight: "clamp" });

  // Particle grid
  const particles = Array.from({ length: 24 }, (_, i) => i);

  return (
    <AbsoluteFill style={{ background: C.bg, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      {/* Animated grid dots */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", opacity: 0.15 }}>
        {particles.map((i) => {
          const x = (i % 6) * (1920 / 5);
          const y = Math.floor(i / 6) * (1080 / 3);
          const pulse = 0.4 + 0.6 * Math.sin(frame / 30 + i * 0.7);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: y,
                width: 4,
                height: 4,
                borderRadius: "50%",
                background: C.accent2,
                opacity: pulse,
              }}
            />
          );
        })}
      </div>

      {/* Logo mark */}
      <div style={{ transform: `scale(${logoScale})`, marginBottom: 32 }}>
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: 24,
            background: `linear-gradient(135deg, ${C.accent}, ${C.accent2})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 48,
            boxShadow: `0 0 40px ${C.accent}44`,
          }}
        >
          ⚡
        </div>
      </div>

      {/* Title */}
      <div
        style={{
          opacity: titleOp,
          transform: `translateY(${titleY}px)`,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 64,
            fontWeight: 800,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            background: `linear-gradient(135deg, ${C.accent}, ${C.accent2})`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            lineHeight: 1.1,
            letterSpacing: "-1px",
          }}
        >
          Claude Code
        </div>
        <div
          style={{
            fontSize: 40,
            fontWeight: 700,
            color: C.text,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            marginTop: 8,
          }}
        >
          프로 설정 가이드
        </div>
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subOp,
          marginTop: 20,
          fontSize: 22,
          color: C.dim,
          fontFamily: "'Segoe UI', system-ui, sans-serif",
          textAlign: "center",
        }}
      >
        자동화 · 스킬 · 에이전트 · 훅
      </div>
    </AbsoluteFill>
  );
}

// ─── Scene 2: Stats (3-6s = 90f) ─────────────────────────────────
const STATS = [
  { num: 87, label: "스킬", color: C.accent3, icon: "🧠" },
  { num: 80, label: "에이전트", color: C.accent2, icon: "🤖" },
  { num: 45, label: "명령어", color: C.accent4, icon: "⌨️" },
  { num: 4, label: "자동 훅", color: C.accent, icon: "🪝" },
];

function StatCard({ stat, index }: { stat: (typeof STATS)[0]; index: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = index * 10;
  const sp = useSpring(frame, fps, delay, 18);
  const opacity = interpolate(sp, [0, 1], [0, 1]);
  const y = interpolate(sp, [0, 1], [50, 0]);

  const countProgress = interpolate(frame, [delay, delay + 40], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const displayNum = Math.round(countProgress * stat.num);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderTop: `3px solid ${stat.color}`,
        borderRadius: 16,
        padding: "32px 40px",
        textAlign: "center",
        width: 340,
        boxShadow: `0 8px 32px #0006`,
      }}
    >
      <div style={{ fontSize: 40, marginBottom: 8 }}>{stat.icon}</div>
      <div
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: stat.color,
          fontFamily: "monospace",
          lineHeight: 1,
        }}
      >
        {displayNum}
      </div>
      <div
        style={{
          fontSize: 24,
          color: C.dim,
          fontFamily: "'Segoe UI', system-ui, sans-serif",
          marginTop: 8,
          fontWeight: 600,
        }}
      >
        {stat.label}
      </div>
    </div>
  );
}

function SceneStats() {
  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 48,
      }}
    >
      <FadeSlide>
        <div
          style={{
            fontSize: 30,
            color: C.dim,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            letterSpacing: "4px",
            textTransform: "uppercase",
          }}
        >
          설정 팩 포함 내용
        </div>
      </FadeSlide>
      <div style={{ display: "flex", gap: 24 }}>
        {STATS.map((s, i) => (
          <StatCard key={i} stat={s} index={i} />
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ─── Scene 3: Concepts (6-10s = 120f) ────────────────────────────
const CONCEPTS = [
  {
    tag: "SKILL",
    tagColor: "#2d3a1f",
    tagText: C.accent3,
    title: "스킬",
    desc: "전문 지식을 Claude에 주입\n'이 작업은 이렇게 해라'",
    example: "TDD · 디버깅 · 설계",
    border: C.accent3,
    icon: "🧩",
  },
  {
    tag: "AGENT",
    tagColor: "#1f2d3a",
    tagText: C.accent2,
    title: "에이전트",
    desc: "전문가 분신이 서브로 실행\n메인 컨텍스트를 깨끗하게",
    example: "code-reviewer · security",
    border: C.accent2,
    icon: "🤖",
  },
  {
    tag: "COMMAND",
    tagColor: "#2d1f3a",
    tagText: C.accent4,
    title: "슬래시 명령어",
    desc: "/명령어로 원클릭 실행\n스킬 + 에이전트 자동 조합",
    example: "/code-review · /plan",
    border: C.accent4,
    icon: "⚡",
  },
  {
    tag: "HOOK",
    tagColor: "#3a2d1f",
    tagText: C.accent,
    title: "훅",
    desc: "이벤트 발생 시 자동 실행\n설정하면 신경 끄기",
    example: "빌드 체크 · 리뷰 자동화",
    border: C.accent,
    icon: "🪝",
  },
];

function ConceptCard({ c, index }: { c: (typeof CONCEPTS)[0]; index: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = index * 12;
  const sp = useSpring(frame, fps, delay, 200);
  const opacity = interpolate(sp, [0, 1], [0, 1]);
  const x = interpolate(sp, [0, 1], [-30, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderLeft: `4px solid ${c.border}`,
        borderRadius: 12,
        padding: "24px 28px",
        flex: 1,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 28 }}>{c.icon}</span>
        <span
          style={{
            background: c.tagColor,
            color: c.tagText,
            fontSize: 11,
            fontWeight: 700,
            padding: "3px 8px",
            borderRadius: 4,
            fontFamily: "monospace",
          }}
        >
          {c.tag}
        </span>
        <span
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: C.text,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
          }}
        >
          {c.title}
        </span>
      </div>
      <div
        style={{
          fontSize: 15,
          color: C.dim,
          fontFamily: "'Segoe UI', system-ui, sans-serif",
          lineHeight: 1.6,
          whiteSpace: "pre-line",
        }}
      >
        {c.desc}
      </div>
      <div
        style={{
          marginTop: 12,
          fontSize: 13,
          color: c.border,
          fontFamily: "monospace",
          background: C.surface2,
          padding: "4px 10px",
          borderRadius: 6,
          display: "inline-block",
        }}
      >
        {c.example}
      </div>
    </div>
  );
}

function SceneConcepts() {
  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 80px",
        gap: 32,
      }}
    >
      <FadeSlide>
        <div
          style={{
            fontSize: 30,
            color: C.dim,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            letterSpacing: "4px",
            textTransform: "uppercase",
          }}
        >
          핵심 개념
        </div>
      </FadeSlide>
      <div style={{ display: "flex", gap: 20, width: "100%" }}>
        {CONCEPTS.map((c, i) => (
          <ConceptCard key={i} c={c} index={i} />
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ─── Scene 4: Features (10-14s = 120f) ───────────────────────────
const FEATURES = [
  { icon: "🔄", text: "세션 종료 시 빌드 에러 자동 감지" },
  { icon: "👁️", text: "코드 리뷰 서브에이전트 자동 실행" },
  { icon: "⚡", text: "작업 유형별 스킬 자동 활성화" },
  { icon: "🌐", text: "87개 전문 스킬 즉시 활용" },
];

function FeatureRow({ f, index }: { f: (typeof FEATURES)[0]; index: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = index * 15;
  const sp = useSpring(frame, fps, delay, 200);
  const opacity = interpolate(sp, [0, 1], [0, 1]);
  const x = interpolate(sp, [0, 1], [60, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: "flex",
        alignItems: "center",
        gap: 20,
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        padding: "18px 28px",
      }}
    >
      <span style={{ fontSize: 32 }}>{f.icon}</span>
      <span
        style={{
          fontSize: 22,
          color: C.text,
          fontFamily: "'Segoe UI', system-ui, sans-serif",
          fontWeight: 500,
        }}
      >
        {f.text}
      </span>
    </div>
  );
}

function SceneFeatures() {
  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 160px",
        gap: 24,
      }}
    >
      <FadeSlide>
        <div
          style={{
            fontSize: 30,
            color: C.dim,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            letterSpacing: "4px",
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          자동화 기능
        </div>
      </FadeSlide>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 16,
          width: "100%",
        }}
      >
        {FEATURES.map((f, i) => (
          <FeatureRow key={i} f={f} index={i} />
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ─── Scene 5: Outro (14-15s = 30f) ───────────────────────────────
function SceneOutro() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = useSpring(frame, fps, 0, 200);
  const opacity = interpolate(sp, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Glow circle */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${C.accent}22 0%, transparent 70%)`,
        }}
      />

      <div style={{ opacity, textAlign: "center", zIndex: 1 }}>
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            background: `linear-gradient(135deg, ${C.accent}, ${C.accent2}, ${C.accent3})`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: 16,
          }}
        >
          지금 시작하세요
        </div>
        <div
          style={{
            fontSize: 24,
            color: C.dim,
            fontFamily: "'Segoe UI', system-ui, sans-serif",
          }}
        >
          Claude Code × 프로 설정 팩
        </div>

        {/* Install command */}
        <div
          style={{
            marginTop: 32,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: "16px 40px",
            fontFamily: "monospace",
            fontSize: 22,
            color: C.accent3,
            display: "inline-block",
          }}
        >
          bash install.sh
        </div>
      </div>
    </AbsoluteFill>
  );
}

// ─── Main Composition ────────────────────────────────────────────
export function ClaudeCodePromo() {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Audio
        src={staticFile("bgm.wav")}
        volume={(f) =>
          interpolate(
            f,
            [0, fps, 13 * fps, 15 * fps],
            [0, 0.55, 0.55, 0],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          )
        }
      />
      <Series>
        {/* Scene 1: Intro 3s */}
        <Series.Sequence durationInFrames={90} premountFor={30}>
          <SceneIntro />
        </Series.Sequence>
        {/* Scene 2: Stats 3s */}
        <Series.Sequence durationInFrames={90} premountFor={30}>
          <SceneStats />
        </Series.Sequence>
        {/* Scene 3: Concepts 4s */}
        <Series.Sequence durationInFrames={120} premountFor={30}>
          <SceneConcepts />
        </Series.Sequence>
        {/* Scene 4: Features 4s */}
        <Series.Sequence durationInFrames={120} premountFor={30}>
          <SceneFeatures />
        </Series.Sequence>
        {/* Scene 5: Outro 1s */}
        <Series.Sequence durationInFrames={30} premountFor={10}>
          <SceneOutro />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
}
