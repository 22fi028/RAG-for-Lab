// [ROLE] 管理画面 (文書アップロードと一覧表示)
// [DEPS] components/Header.tsx, components/admin/UploadArea.tsx, components/admin/DocumentTable.tsx, hooks/useDocuments.ts
// [CALLED_BY] Next.js framework (route /admin)

"use client";

import Header from "@/components/Header";
import UploadArea from "@/components/admin/UploadArea";
import DocumentTable from "@/components/admin/DocumentTable";
import { useDocuments } from "@/hooks/useDocuments";

export default function AdminPage() {
  const { documents, uploading, uploadDocument, deleteDocument } =
    useDocuments();

  return (
    <div className="h-screen flex flex-col">
      <Header showAdminLink={false} showHomeLink />
      <main className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-5xl mx-auto p-6 space-y-6">
          <section>
            <h2 className="text-lg font-semibold mb-3">文書アップロード</h2>
            <UploadArea
              uploading={uploading}
              onUpload={async (file) => {
                await uploadDocument(file);
              }}
            />
          </section>
          <section>
            <h2 className="text-lg font-semibold mb-3">登録済み文書</h2>
            <DocumentTable
              documents={documents}
              onDelete={deleteDocument}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
