// frontend/src/components/overlay/TabBar.tsx
const TEAL = "#14d9be";
const BG = "rgba(9,12,18,0.72)";
const BORDER = "rgba(255,255,255,0.14)";

const TABS = [
  { label: "AI", icon: "🤖" },
  { label: "Timers", icon: "⏱" },
  { label: "Gold", icon: "💰" },
  { label: "Buffs", icon: "🐉" },
  { label: "Ults", icon: "⚡" },
];

interface TabBarProps {
  active: number;
  onSwitch: (index: number) => void;
}

export function TabBar({ active, onSwitch }: TabBarProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: 2,
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 7,
        padding: "4px 6px",
        marginBottom: 4,
        boxShadow: "0 12px 32px rgba(0,0,0,0.3)",
      }}
    >
      {TABS.map((tab, i) => (
        <button
          key={tab.label}
          onClick={() => onSwitch(i)}
          style={{
            padding: "4px 10px",
            background: active === i ? "linear-gradient(180deg, #19f0d2, #0da78f)" : "transparent",
            color: active === i ? "#06100f" : "#aab1c3",
            border: "none",
            borderRadius: 5,
            cursor: "pointer",
            fontSize: 12,
            fontWeight: active === i ? 700 : 400,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          {tab.icon} {tab.label}
        </button>
      ))}
    </div>
  );
}
