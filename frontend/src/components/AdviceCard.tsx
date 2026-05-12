interface Props {
  role?: "user" | "buddy" | "system";
  text: string;
  source?: "ai" | "opgg" | "proactive" | "status";
  createdAt?: string;
}

const SOURCE_STYLES = {
  ai: {
    label: "AI 코치",
    icon: "AI",
    color: "#16e0c5",
    border: "rgba(22, 224, 197, 0.42)",
    background: "linear-gradient(180deg, rgba(18, 21, 30, 0.80), rgba(6, 8, 13, 0.74))",
  },
  opgg: {
    label: "OP.GG",
    icon: "OP",
    color: "#6bb6ff",
    border: "rgba(107, 182, 255, 0.66)",
    background: "linear-gradient(180deg, rgba(12, 27, 46, 0.84), rgba(6, 10, 18, 0.76))",
  },
  proactive: {
    label: "패턴 경고",
    icon: "!",
    color: "#ffc857",
    border: "rgba(255, 200, 87, 0.82)",
    background: "linear-gradient(180deg, rgba(55, 41, 13, 0.78), rgba(13, 10, 6, 0.76))",
  },
  status: {
    label: "상태",
    icon: "...",
    color: "#aab6c8",
    border: "rgba(170, 182, 200, 0.36)",
    background: "linear-gradient(180deg, rgba(18, 21, 30, 0.76), rgba(6, 8, 13, 0.70))",
  },
};

export function AdviceCard({ role = "buddy", text, source = "ai", createdAt }: Props) {
  const variant = role === "buddy" ? SOURCE_STYLES[source] : undefined;
  const label = role === "user" ? "USER" : role === "system" ? "System" : variant?.label ?? "AI 코치";
  const labelColor = role === "user" ? "#9cff57" : role === "system" ? "#ff6d6d" : variant?.color ?? "#16e0c5";
  const textColor = role === "system" ? "#ffb3b3" : role === "user" ? "#f5ffe8" : "#fff2c0";
  const borderColor = role === "system" ? "rgba(255, 109, 109, 0.42)" : role === "user" ? "rgba(156, 255, 87, 0.34)" : variant?.border;
  const background = role === "user"
    ? "linear-gradient(180deg, rgba(19, 40, 24, 0.78), rgba(6, 13, 8, 0.72))"
    : role === "system"
      ? "linear-gradient(180deg, rgba(50, 18, 18, 0.78), rgba(13, 6, 6, 0.72))"
      : variant?.background;

  return (
    <div
      style={{
        background,
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderLeft: `3px solid ${borderColor}`,
        boxShadow: "0 10px 28px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08)",
        borderRadius: 7,
        padding: "8px 11px 9px",
        color: textColor,
        fontSize: 13,
        fontFamily: "Avenir Next, Helvetica Neue, sans-serif",
        lineHeight: 1.42,
        overflowWrap: "anywhere"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 4 }}>
        {role === "buddy" && (
          <span
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              flex: "0 0 auto",
              background: `${labelColor}22`,
              border: `1px solid ${labelColor}88`,
              color: labelColor,
              fontSize: source === "proactive" ? 14 : 9,
              fontWeight: 800,
              lineHeight: 1,
            }}
          >
            {variant?.icon}
          </span>
        )}
        <span style={{ color: labelColor, fontWeight: 800, fontSize: 11 }}>{label}</span>
        {createdAt && (
          <span style={{ color: "rgba(232, 238, 247, 0.46)", fontSize: 10, marginLeft: "auto" }}>{createdAt}</span>
        )}
      </div>
      <div>{text}</div>
    </div>
  );
}
