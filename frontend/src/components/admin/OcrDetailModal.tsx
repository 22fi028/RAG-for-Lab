// [ROLE] OCR詳細ビューアモーダル: 元画像にバウンディングボックスをオーバーレイ表示し、サマリーとブロック一覧を提示する
// [DEPS] lib/types.ts (API_BASE_URL)
// [CALLED_BY] components/admin/DocumentTable.tsx

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/types";
import OcrTextEditorModal from "./OcrTextEditorModal";

type OcrBlock = {
  text: string;
  confidence: number;
  bbox: [number, number, number, number]; // [xmin, ymin, xmax, ymax]
};

type OcrDetail = {
  avg_confidence: number;
  low_conf_count: number;
  blocks: OcrBlock[];
};

type Props = {
  docId: string;
  docTitle: string;
  onClose: () => void;
};

type HoverState = {
  block: OcrBlock;
  // 画面座標（ツールチップ位置）
  clientX: number;
  clientY: number;
};

// confidence に応じた色（緑/黄/赤）
function bboxFill(confidence: number): string {
  if (confidence >= 0.8) return "rgba(34, 197, 94, 0.6)"; // green-500
  if (confidence >= 0.6) return "rgba(234, 179, 8, 0.6)"; // yellow-500
  return "rgba(239, 68, 68, 0.6)"; // red-500
}

function bboxStroke(confidence: number): string {
  if (confidence >= 0.8) return "rgba(21, 128, 61, 1)"; // green-700
  if (confidence >= 0.6) return "rgba(161, 98, 7, 1)"; // yellow-700
  return "rgba(185, 28, 28, 1)"; // red-700
}

function confidenceTextClass(confidence: number): string {
  if (confidence >= 0.8) return "text-green-700";
  if (confidence >= 0.6) return "text-yellow-700";
  return "text-red-700";
}

function confidenceDot(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-500";
  if (confidence >= 0.6) return "bg-yellow-500";
  return "bg-red-500";
}

export default function OcrDetailModal({ docId, docTitle, onClose }: Props) {
  const [data, setData] = useState<OcrDetail | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<HoverState | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  // モーダル表示中は背景スクロールを停止する
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  // ESC キーで閉じる（編集モーダル表示中は編集モーダル側に処理を譲る）
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (showEditor) return;
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, showEditor]);

  // OCRデータ取得 + 画像ロード
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setData(null);
    setImageLoaded(false);
    imageRef.current = null;

    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/ocr`);
        if (!res.ok) {
          throw new Error(`OCRデータの取得に失敗しました (HTTP ${res.status})`);
        }
        const json = (await res.json()) as OcrDetail;
        if (cancelled) return;
        setData(json);

        const img = new Image();
        img.onload = () => {
          if (cancelled) return;
          imageRef.current = img;
          setImageLoaded(true);
        };
        img.onerror = () => {
          if (!cancelled) setError("元画像の読み込みに失敗しました");
        };
        img.src = `${API_BASE_URL}/api/documents/${docId}/image`;
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "読み込みに失敗しました");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [docId]);

  // Canvas 描画: 画像 → BBオーバーレイ
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    const img = imageRef.current;
    if (!canvas || !container || !img || !data) return;

    const containerWidth = Math.max(container.clientWidth, 1);
    const scale = containerWidth / img.naturalWidth;
    const canvasWidth = containerWidth;
    const canvasHeight = img.naturalHeight * scale;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);

    for (const block of data.blocks) {
      const [x1, y1, x2, y2] = block.bbox;
      const x = x1 * scale;
      const y = y1 * scale;
      const w = (x2 - x1) * scale;
      const h = (y2 - y1) * scale;
      ctx.fillStyle = bboxFill(block.confidence);
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = bboxStroke(block.confidence);
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);
    }
  }, [data]);

  useEffect(() => {
    if (imageLoaded && data) draw();
  }, [imageLoaded, data, draw]);

  // ウィンドウリサイズ時に再描画
  useEffect(() => {
    const onResize = () => draw();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [draw]);

  // マウス位置に重なるブロックを検出（最後に描いた=後ろのブロックを優先）
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !data) return;

    const rect = canvas.getBoundingClientRect();
    // canvas の論理ピクセル → 表示ピクセルへの逆変換
    const canvasX = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const canvasY = ((e.clientY - rect.top) / rect.height) * canvas.height;
    const scale = canvas.width / img.naturalWidth;

    let found: OcrBlock | null = null;
    for (const b of data.blocks) {
      const [x1, y1, x2, y2] = b.bbox;
      if (
        canvasX >= x1 * scale &&
        canvasX <= x2 * scale &&
        canvasY >= y1 * scale &&
        canvasY <= y2 * scale
      ) {
        found = b;
      }
    }

    if (found) {
      setHover({ block: found, clientX: e.clientX, clientY: e.clientY });
    } else if (hover) {
      setHover(null);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        // 編集モーダル表示中は詳細ビューアを一時非表示にする（unmount しないことで状態を保持）
        style={{ display: showEditor ? "none" : "flex" }}
      >
      <div
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="font-semibold truncate pr-4">
            OCR詳細: <span className="text-gray-700">{docTitle}</span>
          </h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowEditor(true)}
              className="text-sm text-blue-700 hover:text-blue-900 px-2 py-1 border border-blue-200 rounded hover:bg-blue-50"
            >
              ✏️ テキストを編集
            </button>
            <button
              type="button"
              onClick={onClose}
              className="text-sm text-gray-600 hover:text-gray-900 px-2 py-1"
              aria-label="閉じる"
            >
              ✕ 閉じる
            </button>
          </div>
        </div>

        {/* ボディ: 左=画像+BB, 右=サマリー+ブロック一覧 */}
        <div className="flex-1 flex overflow-hidden">
          <div
            ref={containerRef}
            className="flex-1 overflow-auto p-4 bg-gray-50 relative"
          >
            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">
                {error}
              </div>
            )}
            {!error && !imageLoaded && (
              <p className="text-sm text-gray-500">読み込み中...</p>
            )}
            {!error && (
              <canvas
                ref={canvasRef}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => setHover(null)}
                className="block max-w-full h-auto"
                style={{ display: imageLoaded ? "block" : "none" }}
              />
            )}
            {hover && (
              <div
                className="fixed pointer-events-none bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg max-w-xs"
                style={{
                  left: hover.clientX + 12,
                  top: hover.clientY + 12,
                  zIndex: 60,
                }}
              >
                <div className="font-medium break-all">{hover.block.text}</div>
                <div className="text-[11px] opacity-80">
                  信頼度 {Math.round(hover.block.confidence * 100)}%
                </div>
              </div>
            )}
          </div>

          <aside className="w-72 border-l border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200 text-sm space-y-1">
              <h3 className="font-semibold mb-2">📊 サマリー</h3>
              {!data && !error && (
                <p className="text-xs text-gray-500">読み込み中...</p>
              )}
              {data && (
                <>
                  <div className="flex justify-between">
                    <span className="text-gray-600">平均信頼度</span>
                    <span className={confidenceTextClass(data.avg_confidence)}>
                      {Math.round(data.avg_confidence * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">低信頼ブロック</span>
                    <span>{data.low_conf_count}件</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">総ブロック数</span>
                    <span>{data.blocks.length}件</span>
                  </div>
                </>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="font-semibold mb-2 text-sm">📋 ブロック一覧</h3>
              {data && data.blocks.length === 0 && (
                <p className="text-xs text-gray-500">ブロックがありません。</p>
              )}
              {data && (
                <ul className="space-y-1">
                  {data.blocks.map((b, i) => (
                    <li
                      key={i}
                      className="text-xs flex items-start gap-2 py-1 border-b border-gray-100 last:border-0"
                    >
                      <span
                        className={`inline-block w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${confidenceDot(
                          b.confidence
                        )}`}
                      />
                      <span className="flex-1 break-all">{b.text}</span>
                      <span
                        className={`flex-shrink-0 ${confidenceTextClass(
                          b.confidence
                        )}`}
                      >
                        {Math.round(b.confidence * 100)}%
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      </div>
      </div>

      {showEditor && (
        <OcrTextEditorModal
          docId={docId}
          docTitle={docTitle}
          onClose={() => setShowEditor(false)}
          onSaved={() => setShowEditor(false)}
        />
      )}
    </>
  );
}
