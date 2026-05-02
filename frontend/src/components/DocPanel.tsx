// [ROLE] 根拠チップクリック時に参照箇所(最大200文字)とメタデータを表示するパネル(トグル時 w-0 + opacity-0)
// [DEPS] lib/types.ts
// [CALLED_BY] app/page.tsx

"use client";

import { Source } from "@/lib/types";

type Props = {
  visible: boolean;
  source: Source | null;
};

export default function DocPanel({ visible, source }: Props) {
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
              <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded">
                <p className="text-[11px] text-blue-800">
                  ※ 抜粋テキストの取得は今後のフェーズで実装予定です。現在はメタデータのみ表示しています。
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
