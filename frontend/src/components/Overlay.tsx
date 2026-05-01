import { useEffect, useRef, useState } from "react";

import { useWebSocket } from "../hooks/useWebSocket";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";

export function Overlay() {
  const { lastError, isConnected, audioQueue, messages, sendQuery } = useWebSocket();
  const [language, setLanguage] = useState("en");
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
        sendQuery("What should I do right now?", language);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [language, sendQuery]);

  useEffect(() => {
    return window.riftBuddy?.onRequestAdvice(() => {
      sendQuery("What should I do right now?", language);
    });
  }, [language, sendQuery]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [lastError, messages]);

  return (
    <div
      style={{
        width: 500,
        height: 340,
        padding: 8,
        boxSizing: "border-box",
        pointerEvents: "auto"
      }}
    >
      <StatusBar isConnected={isConnected} language={language} onLanguageChange={setLanguage} />
      <div
        ref={scrollRef}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          maxHeight: 306,
          overflowY: "auto",
          paddingRight: 4,
          scrollbarWidth: "thin"
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
