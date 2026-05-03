interface Props {
  role?: "user" | "buddy" | "system";
  text: string;
}

export function AdviceCard({ role = "buddy", text }: Props) {
  const label = role === "user" ? "USER" : role === "system" ? "System" : "Buddy";
  const labelColor = role === "user" ? "#9cff57" : role === "system" ? "#ff6d6d" : "#16e0c5";
  const textColor = role === "system" ? "#ffb3b3" : role === "user" ? "#f5ffe8" : "#ffe66d";

  return (
    <div
      style={{
        background: "linear-gradient(180deg, rgba(18, 21, 30, 0.78), rgba(6, 8, 13, 0.74))",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        boxShadow: "0 10px 28px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08)",
        borderRadius: 7,
        padding: "9px 12px",
        color: textColor,
        fontSize: 13,
        fontFamily: "Avenir Next, Helvetica Neue, sans-serif",
        lineHeight: 1.42,
        overflowWrap: "anywhere"
      }}
    >
      <span style={{ color: labelColor, fontWeight: "bold" }}>{label}: </span>
      {text}
    </div>
  );
}
