// [ROLE] 会話一覧の取得・新規作成・削除・特定会話の詳細取得を担うReact Hook
// [DEPS] lib/types.ts
// [CALLED_BY] components/SideBar.tsx, app/page.tsx

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  API_BASE_URL,
  Conversation,
  ConversationDetail,
} from "@/lib/types";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: Conversation[] = await res.json();
      setConversations(data);
    } catch (e) {
      console.error("fetchConversations failed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  const createConversation = useCallback(
    async (title?: string): Promise<Conversation | null> => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title ?? null }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const created: Conversation = await res.json();
        setConversations((prev) => [created, ...prev]);
        return created;
      } catch (e) {
        console.error("createConversation failed:", e);
        return null;
      }
    },
    []
  );

  const deleteConversation = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) throw new Error(`status ${res.status}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (e) {
      console.error("deleteConversation failed:", e);
    }
  }, []);

  const getConversation = useCallback(
    async (id: string): Promise<ConversationDetail | null> => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/conversations/${id}`);
        if (!res.ok) throw new Error(`status ${res.status}`);
        return (await res.json()) as ConversationDetail;
      } catch (e) {
        console.error("getConversation failed:", e);
        return null;
      }
    },
    []
  );

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return {
    conversations,
    loading,
    refetch: fetchConversations,
    createConversation,
    deleteConversation,
    getConversation,
  };
}
