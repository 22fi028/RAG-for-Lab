// [ROLE] アプリケーション共通ヘッダー（タイトル・モデルバッジ・履歴/文書/管理画面トグルボタン）
// [DEPS] なし
// [CALLED_BY] app/page.tsx, app/admin/page.tsx

"use client";

import Link from "next/link";

type Props = {
  modelName?: string;
  showSidebar?: boolean;
  showDocPanel?: boolean;
  onToggleSidebar?: () => void;
  onToggleDocPanel?: () => void;
  showAdminLink?: boolean;
  showHomeLink?: boolean;
};

export default function Header({
  modelName = "Qwen3-8B",
  showSidebar,
  showDocPanel,
  onToggleSidebar,
  onToggleDocPanel,
  showAdminLink = true,
  showHomeLink = false,
}: Props) {
  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold">研究室特化型RAG</h1>
        <span className="px-2 py-0.5 text-[11px] rounded-full bg-green-100 text-green-800 border border-green-200">
          {modelName}
        </span>
      </div>
      <div className="flex items-center gap-2">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className={`px-3 py-1 text-xs rounded border transition-colors ${
              showSidebar
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            履歴 {showSidebar ? "●" : "○"}
          </button>
        )}
        {onToggleDocPanel && (
          <button
            type="button"
            onClick={onToggleDocPanel}
            className={`px-3 py-1 text-xs rounded border transition-colors ${
              showDocPanel
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            文書 {showDocPanel ? "●" : "○"}
          </button>
        )}
        {showAdminLink && (
          <Link
            href="/admin"
            className="px-3 py-1 text-xs rounded border bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
          >
            管理
          </Link>
        )}
        {showHomeLink && (
          <Link
            href="/"
            className="px-3 py-1 text-xs rounded border bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
          >
            チャットへ戻る
          </Link>
        )}
      </div>
    </header>
  );
}
