// frontend/src/components/overlay/GoldTab.tsx

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const RED = "#e84057";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

interface GoldTabProps {
  allyGold: number;
  enemyGold: number;
  goldDiff: number;
  allyChampions: string[];
  enemyChampions: string[];
}

function goldColor(diff: number) {
  return diff > 0 ? TEAL : diff < 0 ? RED : MUTED;
}

export function GoldTab({ allyGold, enemyGold, goldDiff, allyChampions, enemyChampions }: GoldTabProps) {
  const sign = goldDiff >= 0 ? "+" : "";
  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>💰 GOLD TRACKER</p>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr", gap: "4px 12px", fontSize: 12 }}>
        <span style={{ color: MUTED }}></span>
        <span style={{ color: TEAL, fontWeight: 700 }}>아군</span>
        <span style={{ color: RED, fontWeight: 700 }}>적군</span>

        <span style={{ color: MUTED }}>Total</span>
        <span style={{ color: TEXT }}>{allyGold.toLocaleString()}</span>
        <span style={{ color: TEXT }}>{enemyGold.toLocaleString()}</span>

        {allyChampions.map((champ, i) => (
          <>
            <span key={`name-${i}`} style={{ color: MUTED, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 70 }}>{champ}</span>
            <span key={`ally-${i}`} style={{ color: TEXT }}>—</span>
            <span key={`enemy-${i}`} style={{ color: TEXT }}>{enemyChampions[i] ?? "—"}</span>
          </>
        ))}
      </div>
      <p style={{ color: goldColor(goldDiff), fontSize: 13, fontWeight: 700, margin: "10px 0 0" }}>
        차이: {sign}{goldDiff.toLocaleString()}
      </p>
    </div>
  );
}
