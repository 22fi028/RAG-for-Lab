// [ROLE] 文書一覧テーブル(タイトル/種別/チャンク数/信頼度バッジ/ステータスバッジ/登録日/削除ボタン)・信頼度クリックでOCR詳細モーダルを開く
// [DEPS] hooks/useDocuments.ts, lib/types.ts, components/admin/OcrDetailModal.tsx
// [CALLED_BY] app/admin/page.tsx

"use client";

import { useState } from "react";
import { DocumentRecord, DocumentStatus } from "@/lib/types";
import OcrDetailModal from "./OcrDetailModal";

type Props = {
  documents: DocumentRecord[];
  onDelete: (id: string) => void;
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "待機中",
  indexing: "処理中",
  indexed: "完了",
  error: "エラー",
};

function statusBadgeClass(status: DocumentStatus): string {
  switch (status) {
    case "pending":
      return "bg-gray-200 text-gray-700";
    case "indexing":
      return "bg-yellow-100 text-yellow-800 animate-pulse";
    case "indexed":
      return "bg-green-100 text-green-800";
    case "error":
      return "bg-red-100 text-red-800";
  }
}

function confidenceBadge(score: number) {
  const pct = Math.round(score * 100);
  if (score >= 0.8) {
    return (
      <span className="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded-full">
        {pct}%
      </span>
    );
  }
  if (score >= 0.6) {
    return (
      <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-0.5 rounded-full">
        {pct}%
      </span>
    );
  }
  return (
    <span className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded-full">
      {pct}%
    </span>
  );
}

function ConfidenceCell({
  doc,
  onOpen,
}: {
  doc: DocumentRecord;
  onOpen: (doc: DocumentRecord) => void;
}) {
  if (doc.source_type !== "ocr") {
    return <span className="text-gray-400 text-xs">-</span>;
  }
  if (typeof doc.avg_confidence !== "number") {
    return <span className="text-gray-400 text-xs">-</span>;
  }
  return (
    <button
      type="button"
      onClick={() => onOpen(doc)}
      className="cursor-pointer hover:opacity-80 transition-opacity"
      title="OCR詳細を表示"
      aria-label="OCR詳細を開く"
    >
      {confidenceBadge(doc.avg_confidence)}
    </button>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("ja-JP", {
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function DocumentTable({ documents, onDelete }: Props) {
  const [ocrModalDoc, setOcrModalDoc] = useState<DocumentRecord | null>(null);

  if (documents.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-8 text-center">
        登録済みの文書がありません。
      </p>
    );
  }

  return (
    <>
    <div className="overflow-x-auto border border-gray-200 rounded-lg bg-white">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-600 border-b border-gray-200">
          <tr>
            <th className="text-left px-3 py-2 font-medium">タイトル</th>
            <th className="text-left px-3 py-2 font-medium">種別</th>
            <th className="text-right px-3 py-2 font-medium">チャンク</th>
            <th className="text-left px-3 py-2 font-medium">信頼度</th>
            <th className="text-left px-3 py-2 font-medium">ステータス</th>
            <th className="text-left px-3 py-2 font-medium">登録日</th>
            <th className="text-right px-3 py-2 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((d) => (
            <tr key={d.id} className="border-b border-gray-100 last:border-0">
              <td className="px-3 py-2">
                <p className="font-medium truncate max-w-xs">
                  {d.title || "(無題)"}
                </p>
                {d.error_message && (
                  <p className="text-[11px] text-red-600 mt-1 truncate max-w-xs">
                    {d.error_message}
                  </p>
                )}
              </td>
              <td className="px-3 py-2 uppercase text-xs text-gray-500">
                {d.source_type}
              </td>
              <td className="px-3 py-2 text-right text-xs">
                {d.chunk_count}
              </td>
              <td className="px-3 py-2">
                <ConfidenceCell doc={d} onOpen={setOcrModalDoc} />
              </td>
              <td className="px-3 py-2">
                <span
                  className={`px-2 py-0.5 rounded-full text-[11px] ${statusBadgeClass(
                    d.status
                  )}`}
                >
                  {STATUS_LABEL[d.status]}
                </span>
              </td>
              <td className="px-3 py-2 text-xs text-gray-600">
                {formatDate(d.created_at)}
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`「${d.title || "(無題)"}」を削除しますか?`)) {
                      onDelete(d.id);
                    }
                  }}
                  className="text-xs text-red-600 hover:text-red-800"
                >
                  削除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    {ocrModalDoc && (
      <OcrDetailModal
        docId={ocrModalDoc.id}
        docTitle={ocrModalDoc.title || "(無題)"}
        onClose={() => setOcrModalDoc(null)}
      />
    )}
    </>
  );
}
