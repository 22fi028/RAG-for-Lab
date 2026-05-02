// [ROLE] 文書一覧取得・アップロード・削除・ステータスポーリング(pending/indexing中のみ3秒間隔)・OCR信頼度の後追い取得を担うReact Hook
// [DEPS] lib/types.ts
// [CALLED_BY] components/admin/UploadArea.tsx, components/admin/DocumentTable.tsx, app/admin/page.tsx

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_BASE_URL,
  DocumentRecord,
  DocumentStatus,
} from "@/lib/types";

const POLL_INTERVAL_MS = 3000;
const ACTIVE_STATUSES: DocumentStatus[] = ["pending", "indexing"];

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // 一度試した OCR ID を記録して 404/エラー時の無限再フェッチを防ぐ
  const ocrAttemptedRef = useRef<Set<string>>(new Set());

  const fetchOcrConfidence = useCallback(async (docId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/ocr`);
      if (!res.ok) return null;
      const json = (await res.json()) as { avg_confidence?: number };
      return typeof json.avg_confidence === "number" ? json.avg_confidence : null;
    } catch {
      return null;
    }
  }, []);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: DocumentRecord[] = await res.json();
      // 一覧APIには avg_confidence が含まれないので、既知のキャッシュを保持してマージする
      setDocuments((prev) => {
        const prevMap = new Map(prev.map((p) => [p.id, p]));
        return data.map((d) => ({
          ...d,
          avg_confidence: prevMap.get(d.id)?.avg_confidence,
        }));
      });
    } catch (e) {
      console.error("fetchDocuments failed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshActiveStatuses = useCallback(async () => {
    const targets = (
      await Promise.all(
        documents
          .filter((d) => ACTIVE_STATUSES.includes(d.status))
          .map(async (d) => {
            try {
              const res = await fetch(
                `${API_BASE_URL}/api/documents/${d.id}/status`
              );
              if (!res.ok) return null;
              const json = (await res.json()) as Partial<DocumentRecord> & {
                id?: string;
              };
              return { id: d.id, payload: json };
            } catch {
              return null;
            }
          })
      )
    ).filter(
      (r): r is { id: string; payload: Partial<DocumentRecord> } => r !== null
    );

    if (targets.length === 0) return;

    setDocuments((prev) =>
      prev.map((doc) => {
        const updated = targets.find((t) => t.id === doc.id);
        if (!updated) return doc;
        return { ...doc, ...updated.payload };
      })
    );
  }, [documents]);

  useEffect(() => {
    const hasActive = documents.some((d) => ACTIVE_STATUSES.includes(d.status));
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (hasActive) {
      timerRef.current = setInterval(() => {
        refreshActiveStatuses();
      }, POLL_INTERVAL_MS);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [documents, refreshActiveStatuses]);

  // 索引完了済みの OCR 文書について avg_confidence を後追いで取得する。
  // 既に試行した ID は ocrAttemptedRef に記録し、再フェッチしない。
  useEffect(() => {
    const targets = documents.filter(
      (d) =>
        d.source_type === "ocr" &&
        d.status === "indexed" &&
        d.avg_confidence === undefined &&
        !ocrAttemptedRef.current.has(d.id)
    );
    if (targets.length === 0) return;

    let cancelled = false;
    targets.forEach((d) => ocrAttemptedRef.current.add(d.id));
    (async () => {
      const results = await Promise.all(
        targets.map(async (d) => ({
          id: d.id,
          score: await fetchOcrConfidence(d.id),
        }))
      );
      if (cancelled) return;
      const valid = results.filter(
        (r): r is { id: string; score: number } => typeof r.score === "number"
      );
      if (valid.length === 0) return;
      setDocuments((prev) =>
        prev.map((doc) => {
          const u = valid.find((v) => v.id === doc.id);
          return u ? { ...doc, avg_confidence: u.score } : doc;
        })
      );
    })();

    return () => {
      cancelled = true;
    };
  }, [documents, fetchOcrConfidence]);

  const uploadDocument = useCallback(
    async (file: File): Promise<DocumentRecord | null> => {
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API_BASE_URL}/api/documents`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok && res.status !== 202) {
          throw new Error(`status ${res.status}`);
        }
        await fetchDocuments();
        return (await res.json()) as DocumentRecord;
      } catch (e) {
        console.error("uploadDocument failed:", e);
        return null;
      } finally {
        setUploading(false);
      }
    },
    [fetchDocuments]
  );

  const deleteDocument = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) throw new Error(`status ${res.status}`);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      ocrAttemptedRef.current.delete(id);
    } catch (e) {
      console.error("deleteDocument failed:", e);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    documents,
    loading,
    uploading,
    refetch: fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
}
