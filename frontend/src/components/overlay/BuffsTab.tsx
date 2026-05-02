// frontend/src/components/overlay/BuffsTab.tsx
import type { BuffHolder } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

function formatTime(seconds: number): string {
  const m = Math.floor(Math.max(0, seconds) / 60);
  const s = Math.floor(Math.max(0, seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface BuffsTabProps {
  buffs: BuffHolder[];
  gameTime: number;
}

export function BuffsTab({ buffs, gameTime }: BuffsTabProps) {
  const activeBuffs = buffs.filter((b) => b.expiresAt > gameTime);

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>🐉 MONSTER BUFFS</p>
      {activeBuffs.length === 0 ? (
        <p style={{ color: MUTED, fontSize: 12 }}>활성 버프 없음</p>
      ) : (
        activeBuffs.map((buff, i) => {
          const remaining = buff.expiresAt - gameTime;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ color: MUTED, fontSize: 12, width: 80 }}>{buff.buffName}</span>
              <span style={{ color: buff.team === "ally" ? TEAL : "#e84057", fontSize: 12 }}>{buff.championName}</span>
              <span style={{ color: TEXT, fontSize: 12, marginLeft: "auto" }}>{formatTime(remaining)}</span>
            </div>
          );
        })
      )}
    </div>
  );
}
