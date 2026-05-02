// [ROLE] OCR認識テキストの編集モーダル: GET /ocr/text で取得し、編集後 PUT /ocr/text で保存する
// [DEPS] lib/types.ts (API_BASE_URL)
// [CALLED_BY] components/admin/OcrDetailModal.tsx

"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/types";

type Props = {
  docId: string;
  docTitle: string;
  onClose: () => void;
  onSaved: () => void;
};

type OcrTextResponse = {
  text: string;
  is_corrected: boolean;
};

export default function OcrTextEditorModal({
  docId,
  docTitle,
  onClose,
  onSaved,
}: Props) {
  const [originalText, setOriginalText] = useState<string | null>(null);
  const [text, setText] = useState<string>("");
  const [isCorrected, setIsCorrected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // モーダル表示中は背景スクロールを停止する
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  // ESC キーで閉じる（保存中は無効）
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !saving) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, saving]);

  // OCRテキスト取得
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/documents/${docId}/ocr/text`
        );
        if (!res.ok) {
          throw new Error(`テキストの取得に失敗しました (HTTP ${res.status})`);
        }
        const json = (await res.json()) as OcrTextResponse;
        if (cancelled) return;
        setOriginalText(json.text);
        setText(json.text);
        setIsCorrected(json.is_corrected);
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "読み込みに失敗しました");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [docId]);

  const handleSave = async () => {
    if (saving || originalText === null || text === originalText) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/documents/${docId}/ocr/text`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        }
      );
      if (!res.ok) {
        throw new Error(`保存に失敗しました (HTTP ${res.status})`);
      }
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
      setSaving(false);
    }
  };

  const handleBackgroundClick = () => {
    if (!saving) onClose();
  };

  const charCount = text.length;
  const isUnchanged = originalText !== null && text === originalText;
  const canSave = !loading && !saving && !isUnchanged && originalText !== null;

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4"
      onClick={handleBackgroundClick}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="font-semibold truncate pr-4">
            テキスト編集:{" "}
            <span className="text-gray-700">{docTitle}</span>
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="text-sm text-gray-600 hover:text-gray-900 px-2 py-1 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="閉じる"
          >
            ✕ 閉じる
          </button>
        </div>

        {/* 案内 */}
        <div className="px-4 py-2 text-xs bg-blue-50 text-blue-800 border-b border-blue-100">
          ℹ️ OCR認識テキストを編集できます。保存後に管理画面から再インデックスを実行してください。
        </div>

        {/* ボディ */}
        <div className="flex-1 flex flex-col overflow-hidden p-4 min-h-0">
          {error && (
            <div className="mb-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">
              {error}
            </div>
          )}

          {loading ? (
            <p className="text-sm text-gray-500">読み込み中...</p>
          ) : originalText === null ? (
            <p className="text-sm text-gray-500">テキストを取得できませんでした。</p>
          ) : (
            <>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={saving}
                spellCheck={false}
                className="flex-1 w-full min-h-[300px] p-3 border border-gray-300 rounded font-mono text-sm leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50"
              />
              <div className="mt-2 text-xs text-gray-600">
                文字数: {charCount.toLocaleString()}文字
              </div>
            </>
          )}
        </div>

        {/* フッター */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
          <div className="text-xs">
            {isCorrected ? (
              <span className="text-green-700">補正済み ✅</span>
            ) : (
              <span className="text-gray-500">未補正</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              キャンセル
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!canSave}
              className="px-4 py-1.5 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
