// [ROLE] メインチャット画面 (Header / SideBar / ChatArea / DocPanel の3カラム構成)
// [DEPS] components/Header.tsx, components/SideBar.tsx, components/ChatArea.tsx, components/DocPanel.tsx, hooks/useChat.ts, hooks/useConversations.ts
// [CALLED_BY] Next.js framework (route /)

"use client";

import { useCallback, useEffect, useState } from "react";
import Header from "@/components/Header";
import SideBar from "@/components/SideBar";
import ChatArea from "@/components/ChatArea";
import DocPanel from "@/components/DocPanel";
import { useConversations } from "@/hooks/useConversations";
import { useChat } from "@/hooks/useChat";
import { Source } from "@/lib/types";

export default function HomePage() {
  const {
    conversations,
    createConversation,
    deleteConversation,
    getConversation,
    refetch: refetchConversations,
  } = useConversations();

  const [activeId, setActiveId] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showDocPanel, setShowDocPanel] = useState(true);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);

  const { messages, isStreaming, sendMessage, resetMessages } =
    useChat(activeId);

  const handleSelectConversation = useCallback(
    async (id: string) => {
      setActiveId(id);
      setSelectedSource(null);
      const detail = await getConversation(id);
      if (detail) {
        resetMessages(detail.messages ?? []);
      } else {
        resetMessages([]);
      }
    },
    [getConversation, resetMessages]
  );

  const handleCreate = useCallback(async () => {
    const created = await createConversation();
    if (created) {
      setActiveId(created.id);
      setSelectedSource(null);
      resetMessages([]);
    }
  }, [createConversation, resetMessages]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      if (id === activeId) {
        setActiveId(null);
        resetMessages([]);
      }
    },
    [deleteConversation, activeId, resetMessages]
  );

  const handleSend = useCallback(
    async (text: string) => {
      await sendMessage(text);
      refetchConversations();
    },
    [sendMessage, refetchConversations]
  );

  useEffect(() => {
    if (!activeId && conversations.length > 0) {
      handleSelectConversation(conversations[0].id);
    }
  }, [activeId, conversations, handleSelectConversation]);

  return (
    <div className="h-screen flex flex-col">
      <Header
        showSidebar={showSidebar}
        showDocPanel={showDocPanel}
        onToggleSidebar={() => setShowSidebar((v) => !v)}
        onToggleDocPanel={() => setShowDocPanel((v) => !v)}
      />
      <div className="flex-1 flex overflow-hidden">
        <SideBar
          visible={showSidebar}
          conversations={conversations}
          activeId={activeId}
          onSelect={handleSelectConversation}
          onCreate={handleCreate}
          onDelete={handleDelete}
        />
        <ChatArea
          messages={messages}
          isStreaming={isStreaming}
          onSend={handleSend}
          onSelectSource={(s) => {
            setSelectedSource(s);
            setShowDocPanel(true);
          }}
          conversationReady={activeId !== null}
        />
        <DocPanel visible={showDocPanel} source={selectedSource} />
      </div>
    </div>
  );
}
