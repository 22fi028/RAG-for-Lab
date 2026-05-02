// [ROLE] 文書のドラッグ&ドロップ・ファイル選択アップロードUI(.pdf .pptx .docx .png .jpg .jpeg)
// [DEPS] hooks/useDocuments.ts
// [CALLED_BY] app/admin/page.tsx

"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";

type Props = {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
};

const ACCEPTED = [".pdf", ".pptx", ".docx", ".png", ".jpg", ".jpeg"];

function isAccepted(file: File): boolean {
  const lower = file.name.toLowerCase();
  return ACCEPTED.some((ext) => lower.endsWith(ext));
}

export default function UploadArea({ onUpload, uploading }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    setError(null);
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      if (!isAccepted(file)) {
        setError(`未対応の形式です: ${file.name}`);
        continue;
      }
      await onUpload(file);
    }
  };

  const onDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    await handleFiles(e.dataTransfer.files);
  };

  const onChange = async (e: ChangeEvent<HTMLInputElement>) => {
    await handleFiles(e.target.files);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragOver
            ? "border-gray-900 bg-gray-50"
            : "border-gray-300 bg-white hover:bg-gray-50"
        }`}
      >
        <p className="text-sm text-gray-600 mb-2">
          ファイルをここにドラッグ&ドロップ
        </p>
        <p className="text-xs text-gray-400 mb-4">
          対応形式: {ACCEPTED.join(" / ")}
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-2 text-sm rounded bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-400"
        >
          {uploading ? "アップロード中..." : "ファイルを選択"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          onChange={onChange}
          className="hidden"
        />
      </div>
      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  );
}
