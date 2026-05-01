import { useCallback, useEffect, useRef, useState } from "react";

import type { ServerMessage } from "../types";

export interface ChatMessage {
  role: "user" | "buddy" | "system";
  text: string;
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
  const [audioQueue, setAudioQueue] = useState<ArrayBuffer[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const ws = useRef<WebSocket | null>(null);

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
            setLastError(msg.audio_error ?? null);
            setMessages((items) => [...items.slice(-(MAX_MESSAGES - 1)), { role: "buddy", text: msg.text }]);
          } else if (msg.type === "transcript") {
            setMessages((items) => [...items.slice(-(MAX_MESSAGES - 1)), { role: "user", text: msg.text }]);
          } else if (msg.type === "listening") {
            setMessages((items) => [...items.slice(-(MAX_MESSAGES - 1)), { role: "buddy", text: msg.text }]);
          } else {
            setLastError(msg.message);
            setMessages((items) => [...items.slice(-(MAX_MESSAGES - 1)), { role: "system", text: msg.message }]);
          }
        } else if (event.data instanceof Blob) {
          event.data.arrayBuffer().then((buf) => setAudioQueue((q) => [...q, buf]));
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
  }, []);

  const sendQuery = useCallback((query: string | null, language = "en") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      if (query) {
        setMessages((items) => [...items.slice(-(MAX_MESSAGES - 1)), { role: "user", text: query }]);
      }
      ws.current.send(JSON.stringify({ query, language }));
    }
  }, []);

  return { lastAdvice, lastError, isConnected, audioQueue, messages, sendQuery, wsUrl: WS_URL };
}
