// frontend/src/components/overlay/TimersTab.tsx
import { useEffect, useState } from "react";
import type { ObjectiveTimer } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const MUTED = "#8888aa";
const TEAL = "#00c8a0";
const BG = "rgba(15,17,23,0.90)";

interface TimersTabProps {
  objectives: ObjectiveTimer[];
  gameTime: number;
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div style={{ height: 6, background: "#2a2d3a", borderRadius: 3, overflow: "hidden", flex: 1, marginRight: 8 }}>
      <div style={{ height: "100%", width: `${pct * 100}%`, background: TEAL, borderRadius: 3, transition: "width 1s linear" }} />
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(Math.abs(seconds) / 60);
  const s = Math.floor(Math.abs(seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ObjectiveRow({ obj, gameTime }: { obj: ObjectiveTimer; gameTime: number }) {
  const spawned = gameTime >= obj.spawnAt;
  const isHerald = obj.name === "Herald";
  const heraldDespawn = 19 * 60 + 45;

  if (isHerald && gameTime > heraldDespawn) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ width: 70, color: MUTED, fontSize: 12 }}>{obj.name}</span>
        <span style={{ color: MUTED, fontSize: 12 }}>소멸됨</span>
      </div>
    );
  }

  if (!spawned) {
    const wait = obj.spawnAt - gameTime;
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ width: 70, color: MUTED, fontSize: 12 }}>{obj.name}</span>
        <span style={{ color: MUTED, fontSize: 12 }}>스폰까지 {formatTime(wait)}</span>
      </div>
    );
  }

  if (obj.lastKillAt !== null) {
    const respawnAt = obj.lastKillAt + obj.respawn;
    const remaining = respawnAt - gameTime;
    if (remaining > 0) {
      const progress = 1 - remaining / obj.respawn;
      return (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ width: 70, color: TEXT, fontSize: 12 }}>{obj.name}</span>
          <ProgressBar value={progress} />
          <span style={{ color: TEXT, fontSize: 12, minWidth: 40 }}>{formatTime(remaining)}</span>
        </div>
      );
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
      <span style={{ width: 70, color: TEXT, fontSize: 12 }}>{obj.name}</span>
      <span style={{ color: TEAL, fontSize: 12, fontWeight: 700 }}>ALIVE ✓</span>
    </div>
  );
}

export function TimersTab({ objectives, gameTime }: TimersTabProps) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  void tick;

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>⏱ OBJECTIVE TIMERS</p>
      {objectives.map((obj) => (
        <ObjectiveRow key={obj.name} obj={obj} gameTime={gameTime} />
      ))}
    </div>
  );
}
