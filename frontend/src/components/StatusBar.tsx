interface Props {
  isConnected: boolean;
  language: string;
  onLanguageChange: (language: string) => void;
}

export function StatusBar({ isConnected, language, onLanguageChange }: Props) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 11,
        color: isConnected ? "#00FF88" : "#FF4444",
        fontFamily: "monospace",
        padding: "2px 6px"
      }}
    >
      <span>{isConnected ? "LIVE" : "OFFLINE"}</span>
      <button
        type="button"
        onClick={() => onLanguageChange(language === "ko" ? "en" : "ko")}
        style={{
          border: "1px solid rgba(255,255,255,0.25)",
          background: "rgba(0,0,0,0.55)",
          color: "#FFFFFF",
          borderRadius: 6,
          padding: "2px 6px",
          fontSize: 10,
          fontFamily: "monospace"
        }}
      >
        {language.toUpperCase()}
      </button>
    </div>
  );
}
