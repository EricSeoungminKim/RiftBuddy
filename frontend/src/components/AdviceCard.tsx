interface Props {
  role?: "user" | "buddy" | "system";
  text: string;
}

export function AdviceCard({ role = "buddy", text }: Props) {
  const label = role === "user" ? "USER" : role === "system" ? "System" : "Buddy";
  const labelColor = role === "user" ? "#B7FF6A" : role === "system" ? "#FF6B6B" : "#00BFFF";
  const textColor = role === "system" ? "#FFB3B3" : "#FFD700";

  return (
    <div
      style={{
        background: "rgba(0, 0, 0, 0.75)",
        borderRadius: 8,
        padding: "10px 14px",
        color: textColor,
        fontSize: 14,
        fontFamily: "sans-serif",
        lineHeight: 1.45,
        overflowWrap: "anywhere"
      }}
    >
      <span style={{ color: labelColor, fontWeight: "bold" }}>{label}: </span>
      {text}
    </div>
  );
}
