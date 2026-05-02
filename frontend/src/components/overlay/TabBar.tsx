// frontend/src/components/overlay/TabBar.tsx
const TEAL = "#00c8a0";
const BG = "rgba(15,17,23,0.85)";
const BORDER = "#2a2d3a";

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
        borderRadius: 8,
        padding: "4px 6px",
        marginBottom: 4,
      }}
    >
      {TABS.map((tab, i) => (
        <button
          key={tab.label}
          onClick={() => onSwitch(i)}
          style={{
            padding: "4px 10px",
            background: active === i ? TEAL : "transparent",
            color: active === i ? "#000" : "#aaa",
            border: "none",
            borderRadius: 6,
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
