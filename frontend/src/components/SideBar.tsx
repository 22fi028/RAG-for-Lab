// [ROLE] 会話一覧サイドバー（新規作成・選択・削除・トグル時 w-0 + opacity-0 アニメーション）
// [DEPS] hooks/useConversations.ts, lib/types.ts
// [CALLED_BY] app/page.tsx

"use client";

import { Conversation } from "@/lib/types";

type Props = {
  visible: boolean;
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ja-JP", {
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function SideBar({
  visible,
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: Props) {
  return (
    <aside
      className={`flex-shrink-0 overflow-hidden transition-all duration-200 ease-in-out border-r border-gray-200 bg-white ${
        visible ? "w-[220px] opacity-100" : "w-0 opacity-0"
      }`}
    >
      <div className="w-[220px] h-full flex flex-col">
        <div className="p-3 border-b border-gray-200">
          <button
            type="button"
            onClick={onCreate}
            className="w-full px-3 py-2 text-sm rounded bg-gray-900 text-white hover:bg-gray-800"
          >
            ＋ 新しい会話
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 && (
            <p className="p-4 text-xs text-gray-500">会話がありません</p>
          )}
          <ul>
            {conversations.map((c) => {
              const isActive = c.id === activeId;
              return (
                <li
                  key={c.id}
                  className={`group border-b border-gray-100 ${
                    isActive
                      ? "bg-gray-100 border-l-4 border-l-gray-900"
                      : "border-l-4 border-l-transparent hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center justify-between px-3 py-2">
                    <button
                      type="button"
                      onClick={() => onSelect(c.id)}
                      className="flex-1 text-left"
                    >
                      <p className="text-sm font-medium truncate">
                        {c.title || "新しい会話"}
                      </p>
                      <p className="text-[11px] text-gray-500">
                        {formatDate(c.created_at)}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm("この会話を削除しますか?")) onDelete(c.id);
                      }}
                      className="ml-2 text-xs text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-600"
                      aria-label="削除"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </aside>
  );
}
