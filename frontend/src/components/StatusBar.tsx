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
        color: isConnected ? "#71ff95" : "#ff6363",
        fontFamily: "Avenir Next, Helvetica Neue, sans-serif",
        fontWeight: 800,
        letterSpacing: 0,
        padding: "2px 6px"
      }}
    >
      <span>{isConnected ? "LIVE" : "OFFLINE"}</span>
      <button
        type="button"
        onClick={() => onLanguageChange(language === "ko" ? "en" : "ko")}
        style={{
          border: "1px solid rgba(255,255,255,0.25)",
          background: "rgba(5,8,13,0.68)",
          color: "#FFFFFF",
          borderRadius: 6,
          padding: "2px 6px",
          fontSize: 10,
          fontFamily: "Avenir Next, Helvetica Neue, sans-serif"
        }}
      >
        {language.toUpperCase()}
      </button>
    </div>
  );
}
