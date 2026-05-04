// [ROLE] 根拠チップクリック時に参照箇所(最大200文字)とメタデータを表示するパネル(トグル時 w-0 + opacity-0)
// [DEPS] lib/types.ts (Source, API_BASE_URL)
// [CALLED_BY] app/page.tsx

"use client";

import { useEffect, useState } from "react";
import { Source, API_BASE_URL } from "@/lib/types";

type Props = {
  visible: boolean;
  source: Source | null;
};

export default function DocPanel({ visible, source }: Props) {
  const [excerpt, setExcerpt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!source) {
      setExcerpt(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setExcerpt(null);

    const params = new URLSearchParams({
      title: source.title || "",
      chapter: source.chapter || "",
      page: String(source.page || 0),
    });

    fetch(
      `${API_BASE_URL}/api/documents/chunk-excerpt?${params.toString()}`,
      { signal: controller.signal }
    )
      .then((res) => (res.ok ? res.json() : { content: "" }))
      .then((data) => {
        setExcerpt(typeof data?.content === "string" ? data.content : "");
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setExcerpt("");
        }
      })
      .finally(() => {
        setLoading(false);
      });

    return () => controller.abort();
  }, [source]);

  return (
    <aside
      className={`flex-shrink-0 overflow-hidden transition-all duration-200 ease-in-out border-l border-gray-200 bg-white ${
        visible ? "w-[300px] opacity-100" : "w-0 opacity-0"
      }`}
    >
      <div className="w-[300px] h-full flex flex-col">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold">文書ビューア</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {!source && (
            <p className="text-xs text-gray-500">
              根拠チップをクリックすると、参照箇所がここに表示されます。
            </p>
          )}
          {source && (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-xs text-gray-500">タイトル</p>
                <p className="text-sm font-medium">
                  {source.title || "(無題)"}
                </p>
              </div>
              {source.chapter && (
                <div className="space-y-1">
                  <p className="text-xs text-gray-500">章</p>
                  <p className="text-sm">{source.chapter}</p>
                </div>
              )}
              {source.page > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-gray-500">ページ</p>
                  <p className="text-sm">p.{source.page}</p>
                </div>
              )}
              {loading && (
                <div className="mt-4 p-3 bg-gray-50 border border-gray-100 rounded">
                  <p className="text-xs text-gray-500">読み込み中...</p>
                </div>
              )}
              {!loading && excerpt && excerpt.length > 0 && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded">
                  <p className="text-xs text-blue-900 whitespace-pre-wrap leading-relaxed">
                    {excerpt}
                  </p>
                </div>
              )}
              {!loading && excerpt !== null && excerpt.length === 0 && (
                <div className="mt-4 p-3 bg-gray-50 border border-gray-100 rounded">
                  <p className="text-xs text-gray-500">
                    抜粋テキストは利用できません
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
