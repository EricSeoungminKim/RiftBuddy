import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";
import { TabBar } from "./overlay/TabBar";

export function Overlay() {
  const { isConnected, isLoading, messages, requestPlannedAdvice, requestMatchup, requestItems, requestMacro } = useWebSocket();
  const [language, setLanguage] = useState((import.meta.env.VITE_RIFTBUDDY_RESPONSE_LANGUAGE as string) ?? "ko");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const modifierPressed = event.metaKey || event.ctrlKey;
      if (!modifierPressed || !event.shiftKey) return;
      const key = event.key.toLowerCase();
      if (key === "b") { event.preventDefault(); requestPlannedAdvice(language); }
      else if (key === "c") { event.preventDefault(); requestMatchup(language); }
      else if (key === "1") { event.preventDefault(); requestItems(language); }
      else if (key === "2") { event.preventDefault(); requestMacro(language); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [language, requestPlannedAdvice, requestMatchup, requestItems, requestMacro]);

  useEffect(() => {
    return window.riftBuddy?.onRequestAdvice(() => requestPlannedAdvice(language));
  }, [language, requestPlannedAdvice]);

  useEffect(() => {
    return window.riftBuddy?.onRequestMatchup(() => requestMatchup(language));
  }, [language, requestMatchup]);

  useEffect(() => {
    return window.riftBuddy?.onRequestItems(() => requestItems(language));
  }, [language, requestItems]);

  useEffect(() => {
    return window.riftBuddy?.onRequestMacro(() => requestMacro(language));
  }, [language, requestMacro]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div
      style={{
        width: 420,
        height: 420,
        padding: 10,
        boxSizing: "border-box",
        pointerEvents: "auto",
        background: "linear-gradient(140deg, rgba(9,12,18,0.20), rgba(20,52,48,0.12))",
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
        {messages.map((message, index) => (
          <AdviceCard
            key={message.id ?? `${message.role}-${index}-${message.text}`}
            role={message.role}
            text={message.text}
            source={message.source}
            createdAt={message.createdAt}
            isLoading={isLoading && message.id === "loading-indicator"}
          />
        ))}
      </div>
    </div>
  );
}
