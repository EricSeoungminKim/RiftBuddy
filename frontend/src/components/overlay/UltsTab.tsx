// frontend/src/components/overlay/UltsTab.tsx
import { useEffect, useState } from "react";
import type { UltTimer } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

function formatTime(seconds: number): string {
  const m = Math.floor(Math.max(0, seconds) / 60);
  const s = Math.floor(Math.max(0, seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function effectiveCd(ult: UltTimer): number {
  return ult.baseCd * (1 - ult.cdr);
}

interface UltsTabProps {
  ults: UltTimer[];
  gameTime: number;
}

export function UltsTab({ ults, gameTime }: UltsTabProps) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (ults.length === 0) {
    return (
      <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
        <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 8px" }}>⚡ ULTIMATE TIMERS</p>
        <p style={{ color: MUTED, fontSize: 12 }}>경기 시작 후 데이터 수집 중...</p>
      </div>
    );
  }

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>⚡ ULTIMATE TIMERS</p>
      {ults.map((ult, i) => {
        const cd = effectiveCd(ult);
        const usedAt = ult.lastUsedAt;
        const ready = usedAt === null || gameTime - usedAt >= cd;
        const remaining = usedAt !== null ? Math.max(0, cd - (gameTime - usedAt)) : 0;

        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ color: ult.team === "ally" ? TEAL : "#e84057", fontSize: 12, width: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {ult.championName}
            </span>
            {ready ? (
              <span style={{ color: TEAL, fontSize: 12, fontWeight: 700 }}>READY ✓</span>
            ) : (
              <>
                <div style={{ flex: 1, height: 6, background: "#2a2d3a", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${((cd - remaining) / cd) * 100}%`, background: "#e84057", borderRadius: 3 }} />
                </div>
                <span style={{ color: TEXT, fontSize: 12, minWidth: 40 }}>{formatTime(remaining)}</span>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
