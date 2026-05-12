import { useCallback, useEffect, useRef, useState } from "react";

import type { ServerMessage } from "../types";

export interface ChatMessage {
  role: "user" | "buddy" | "system";
  text: string;
  source?: "ai" | "opgg" | "proactive" | "status";
  createdAt: string;
}

const MAX_MESSAGES = 20;

const WS_TOKEN = import.meta.env.VITE_RIFTBUDDY_WS_TOKEN as string | undefined;
const WS_BASE_URL =
  (import.meta.env.VITE_RIFTBUDDY_WS_URL as string | undefined) ?? "ws://localhost:8001/ws";
const WS_URL = WS_TOKEN
  ? `${WS_BASE_URL}?token=${encodeURIComponent(WS_TOKEN)}`
  : WS_BASE_URL;

export function useWebSocket() {
  const [lastAdvice, setLastAdvice] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const pendingAdviceSource = useRef<ChatMessage["source"]>("ai");

  const appendMessage = useCallback((message: Omit<ChatMessage, "createdAt">) => {
    setMessages((items) => [
      ...items.slice(-(MAX_MESSAGES - 1)),
      { ...message, createdAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) },
    ]);
  }, []);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let isDisposed = false;

    const connect = () => {
      const socket = new WebSocket(WS_URL);
      ws.current = socket;

      socket.onopen = () => setIsConnected(true);
      socket.onclose = () => {
        setIsConnected(false);
        if (!isDisposed) {
          reconnectTimer = window.setTimeout(connect, 1500);
        }
      };

      socket.onmessage = (event) => {
        if (typeof event.data === "string") {
          const msg: ServerMessage = JSON.parse(event.data);
          if (msg.type === "advice") {
            setLastAdvice(msg.text);
            appendMessage({ role: "buddy", text: msg.text, source: pendingAdviceSource.current ?? "ai" });
            pendingAdviceSource.current = "ai";
          } else if (msg.type === "proactive_warning") {
            setLastAdvice(msg.text);
            appendMessage({ role: "buddy", text: msg.text, source: "proactive" });
          } else if (msg.type === "transcript") {
            appendMessage({ role: "user", text: msg.text });
          } else if (msg.type === "game_state") {
            return;
          } else if (msg.type === "game_end") {
            appendMessage({ role: "system", text: "게임이 종료됐어요. 포스트게임 분석을 확인할 수 있어요." });
          } else {
            setLastError(msg.message);
            appendMessage({ role: "system", text: msg.message });
          }
        }
      };
    };

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      ws.current?.close();
    };
  }, [appendMessage]);

  const sendQuery = useCallback((query: string | null, language = "ko") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      pendingAdviceSource.current = "ai";
      if (query) {
        appendMessage({ role: "user", text: query });
      }
      ws.current.send(JSON.stringify({ query, language }));
    }
  }, [appendMessage]);

  const requestPlannedAdvice = useCallback((language = "ko") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      pendingAdviceSource.current = "ai";
      ws.current.send(JSON.stringify({ action: "advice", mode: "planned", query: null, language }));
    }
  }, []);

  const requestMatchup = useCallback((language = "ko") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      pendingAdviceSource.current = "opgg";
      ws.current.send(JSON.stringify({ action: "matchup", query: null, language }));
    }
  }, []);

  const requestItems = useCallback((language = "ko") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      pendingAdviceSource.current = "ai";
      ws.current.send(JSON.stringify({ action: "items", query: null, language }));
    }
  }, []);

  const requestMacro = useCallback((language = "ko") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      pendingAdviceSource.current = "ai";
      ws.current.send(JSON.stringify({ action: "macro", query: null, language }));
    }
  }, []);

  return {
    lastAdvice,
    lastError,
    isConnected,
    messages,
    sendQuery,
    requestPlannedAdvice,
    requestMatchup,
    requestItems,
    requestMacro,
    wsUrl: WS_URL
  };
}
