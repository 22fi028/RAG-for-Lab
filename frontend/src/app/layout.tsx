// [ROLE] Next.js ルートレイアウト・グローバルCSS適用・メタデータ定義
// [DEPS] app/globals.css
// [CALLED_BY] Next.js framework (全ページ)

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "研究室特化型RAG",
  description: "研究室の過去知見を自然言語で検索できるローカルRAGシステム",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="h-full">{children}</body>
    </html>
  );
}
