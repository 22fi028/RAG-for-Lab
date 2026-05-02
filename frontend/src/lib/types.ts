// [ROLE] フロントエンド共通型定義（Message / Conversation / Document / Source）
// [DEPS] なし
// [CALLED_BY] hooks/*, components/*

export type Source = {
  title: string;
  chapter: string;
  page: number;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isError?: boolean;
  isStreaming?: boolean;
  created_at?: string;
};

export type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
};

export type ConversationDetail = Conversation & {
  messages: Message[];
};

export type DocumentStatus = "pending" | "indexing" | "indexed" | "error";

export type DocumentRecord = {
  id: string;
  title: string | null;
  author: string | null;
  year: number | null;
  source_type: string;
  file_path: string | null;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  // OCR文書のみ。一覧APIには含まれず /documents/{id}/ocr から後追いで取得する。
  avg_confidence?: number;
  // OCR文書のみ。corrected_text が保存されているかどうか。
  is_corrected?: boolean;
};

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
