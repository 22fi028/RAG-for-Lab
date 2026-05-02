// [ROLE] SSE受信・メッセージ状態管理・ストリーミング制御のReact Hook
// [DEPS] lib/types.ts
// [CALLED_BY] components/ChatArea.tsx

"use client";

import { useCallback, useRef, useState } from "react";
import { API_BASE_URL, Message, Source } from "@/lib/types";

type SSEPayload =
  | { type: "token"; content: string }
  | { type: "done"; sources: Source[] }
  | { type: "error"; message: string };

function makeId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat(conversationId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const resetMessages = useCallback((initial: Message[] = []) => {
    setMessages(initial);
  }, []);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!conversationId) {
        console.warn("sendMessage called without conversationId");
        return;
      }
      if (!question.trim() || isStreaming) return;

      const userMessage: Message = {
        id: makeId(),
        role: "user",
        content: question,
      };
      const assistantId = makeId();
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            conversation_id: conversationId,
            question,
          }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) {
          throw new Error(`status ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let separatorIndex: number;
          while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
            const rawEvent = buffer.slice(0, separatorIndex);
            buffer = buffer.slice(separatorIndex + 2);
            const dataLines = rawEvent
              .split("\n")
              .filter((l) => l.startsWith("data:"))
              .map((l) => l.slice(5).trimStart());
            if (dataLines.length === 0) continue;
            const dataStr = dataLines.join("\n");
            let payload: SSEPayload;
            try {
              payload = JSON.parse(dataStr) as SSEPayload;
            } catch {
              continue;
            }

            if (payload.type === "token") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + payload.content }
                    : m
                )
              );
            } else if (payload.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        sources: payload.sources,
                        isStreaming: false,
                      }
                    : m
                )
              );
              setIsStreaming(false);
            } else if (payload.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: payload.message,
                        isError: true,
                        isStreaming: false,
                      }
                    : m
                )
              );
              setIsStreaming(false);
            }
          }
        }
      } catch (e) {
        const message =
          e instanceof Error
            ? e.message
            : "通信エラーが発生しました。";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: `通信エラー: ${message}`,
                  isError: true,
                  isStreaming: false,
                }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [conversationId, isStreaming]
  );

  return {
    messages,
    isStreaming,
    sendMessage,
    resetMessages,
  };
}
