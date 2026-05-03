import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";
import { TabBar } from "./overlay/TabBar";

export function Overlay() {
  const { lastError, isConnected, audioQueue, messages, requestVoiceQuestion, requestPlannedAdvice } = useWebSocket();
  const [language, setLanguage] = useState((import.meta.env.VITE_RIFTBUDDY_RESPONSE_LANGUAGE as string) ?? "ko");
  const scrollRef = useRef<HTMLDivElement | null>(null);

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
    return window.riftBuddy?.onRequestAdvice(() => requestPlannedAdvice(language));
  }, [language, requestPlannedAdvice]);

  useEffect(() => {
    return window.riftBuddy?.onRequestVoiceQuestion(() => requestVoiceQuestion(language));
  }, [language, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [lastError, messages]);

  return (
    <div
      style={{
        width: 500,
        height: 420,
        padding: 10,
        boxSizing: "border-box",
        pointerEvents: "auto",
        background: "linear-gradient(140deg, rgba(9,12,18,0.18), rgba(20,52,48,0.09))",
        borderRadius: 10,
      }}
    >
      <StatusBar isConnected={isConnected} language={language} onLanguageChange={setLanguage} />
      <TabBar />
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
          maskImage: "linear-gradient(to bottom, transparent 0, black 18px, black calc(100% - 10px), transparent 100%)",
        }}
      >
        {lastError && <AdviceCard role="system" text={lastError} />}
        {messages.map((message, index) => (
          <AdviceCard key={`${message.role}-${index}-${message.text}`} role={message.role} text={message.text} />
        ))}
      </div>
    </div>
  );
}
