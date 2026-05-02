// [ROLE] チャット表示・メッセージ送信入力・SSEストリーミング表示・根拠チップ表示
// [DEPS] hooks/useChat.ts, lib/types.ts
// [CALLED_BY] app/page.tsx

"use client";

import {
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { Message, Source } from "@/lib/types";

type Props = {
  messages: Message[];
  isStreaming: boolean;
  onSend: (text: string) => void;
  onSelectSource: (source: Source) => void;
  conversationReady: boolean;
};

export default function ChatArea({
  messages,
  isStreaming,
  onSend,
  onSelectSource,
  conversationReady,
}: Props) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = () => {
    const value = input.trim();
    if (!value || isStreaming || !conversationReady) return;
    onSend(value);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const sendDisabled = isStreaming || !conversationReady || input.trim() === "";

  return (
    <section className="flex-1 flex flex-col min-w-0 bg-gray-50">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-sm text-gray-400">
            {conversationReady
              ? "質問を入力してください"
              : "会話を作成または選択してください"}
          </div>
        )}
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              onSelectSource={onSelectSource}
            />
          ))}
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white p-3">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder={
              conversationReady
                ? "質問を入力 (Enter送信 / Shift+Enter改行)"
                : "会話を作成または選択してください"
            }
            disabled={!conversationReady}
            className="flex-1 resize-none rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gray-500 disabled:bg-gray-100"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={sendDisabled}
            className="px-4 py-2 text-sm rounded bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            送信
          </button>
        </div>
      </div>
    </section>
  );
}

function MessageBubble({
  message,
  onSelectSource,
}: {
  message: Message;
  onSelectSource: (s: Source) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-green-100 text-gray-900 px-4 py-2 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  const baseBg = message.isError
    ? "bg-red-100 text-red-900 border border-red-200"
    : "bg-gray-100 text-gray-900";

  return (
    <div className="flex justify-start">
      <div className={`max-w-[80%] rounded-lg ${baseBg} px-4 py-2 text-sm`}>
        <div className="whitespace-pre-wrap">
          {message.content}
          {message.isStreaming && message.content.length === 0 && <BounceDots />}
          {message.isStreaming && message.content.length > 0 && (
            <span className="inline-block w-[1ch] animate-pulse">|</span>
          )}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.sources.map((s, i) => (
              <button
                key={`${s.title}-${s.chapter}-${s.page}-${i}`}
                type="button"
                onClick={() => onSelectSource(s)}
                className="bg-blue-50 text-blue-800 rounded-full text-[11px] px-2 py-0.5 border border-blue-100 hover:bg-blue-100"
              >
                {s.title || "(無題)"}
                {s.chapter ? ` ${s.chapter}` : ""}
                {s.page ? ` p.${s.page}` : ""}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function BounceDots() {
  return (
    <span className="inline-flex gap-1 items-center align-middle">
      <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
      <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
      <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" />
    </span>
  );
}
