import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useGameEvents } from "../hooks/useGameEvents";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";
import { TabBar } from "./overlay/TabBar";
import { TimersTab } from "./overlay/TimersTab";
import { GoldTab } from "./overlay/GoldTab";
import { BuffsTab } from "./overlay/BuffsTab";
import { UltsTab } from "./overlay/UltsTab";

const TAB_AI = 0;
const TAB_TIMERS = 1;
const TAB_GOLD = 2;
const TAB_BUFFS = 3;
const TAB_ULTS = 4;

export function Overlay() {
  const { lastError, isConnected, audioQueue, messages, requestVoiceQuestion, requestPlannedAdvice } = useWebSocket();
  const [language, setLanguage] = useState((import.meta.env.VITE_RIFTBUDDY_RESPONSE_LANGUAGE as string) ?? "ko");
  const [activeTab, setActiveTab] = useState(TAB_AI);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const gameEvents = useGameEvents(messages);

  useEffect(() => {
    if (audioQueue.length === 0) return;
    const buf = audioQueue[audioQueue.length - 1];
    const blob = new Blob([buf], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(() => {});
    return () => URL.revokeObjectURL(url);
  }, [audioQueue]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const modifierPressed = event.metaKey || event.ctrlKey;
      if (modifierPressed && event.shiftKey && event.key.toLowerCase() === "b") {
        event.preventDefault();
        requestPlannedAdvice(language);
      }
      if (modifierPressed && event.shiftKey && event.code === "Space") {
        event.preventDefault();
        requestVoiceQuestion(language);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [language, requestPlannedAdvice, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onRequestAdvice(() => {
      requestPlannedAdvice(language);
    });
  }, [language, requestPlannedAdvice]);

  useEffect(() => {
    return window.riftBuddy?.onRequestVoiceQuestion(() => {
      requestVoiceQuestion(language);
    });
  }, [language, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    return window.riftBuddy?.onTabSwitch?.((tabIndex: number) => {
      setActiveTab(tabIndex);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [lastError, messages]);

  return (
    <div
      style={{
        width: 500,
        height: 420,
        padding: 8,
        boxSizing: "border-box",
        pointerEvents: "auto",
      }}
    >
      <StatusBar isConnected={isConnected} language={language} onLanguageChange={setLanguage} />
      <TabBar active={activeTab} onSwitch={setActiveTab} />

      {activeTab === TAB_AI && (
        <div
          ref={scrollRef}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 360,
            overflowY: "auto",
            paddingRight: 4,
            scrollbarWidth: "thin",
          }}
        >
          {lastError && <AdviceCard role="system" text={lastError} />}
          {messages.map((message, index) => (
            <AdviceCard key={`${message.role}-${index}-${message.text}`} role={message.role} text={message.text} />
          ))}
        </div>
      )}

      {activeTab === TAB_TIMERS && (
        <TimersTab objectives={gameEvents.objectives} gameTime={gameEvents.gameTime} />
      )}

      {activeTab === TAB_GOLD && (
        <GoldTab
          allyGold={gameEvents.allyGold}
          enemyGold={gameEvents.enemyGold}
          goldDiff={gameEvents.goldDiff}
          allyChampions={gameEvents.allyChampions}
          enemyChampions={gameEvents.enemyChampions}
        />
      )}

      {activeTab === TAB_BUFFS && (
        <BuffsTab buffs={gameEvents.buffs} gameTime={gameEvents.gameTime} />
      )}

      {activeTab === TAB_ULTS && (
        <UltsTab ults={gameEvents.ults} gameTime={gameEvents.gameTime} />
      )}
    </div>
  );
}
