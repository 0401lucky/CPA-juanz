import { FormEvent, useState } from "react";

import { uploadCredential } from "../lib/api";


type JsonUploadCardProps = {
  endpoint: "/public/credentials/json" | "/me/credentials/json";
  title: string;
  intro: string;
  onCompleted: (managementCode: string | null, notice: string) => void;
  onCredentialCreated: () => Promise<void> | void;
};

export function JsonUploadCard({
  endpoint,
  title,
  intro,
  onCompleted,
  onCredentialCreated
}: JsonUploadCardProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("请先选择一个 Gemini JSON 文件");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await uploadCredential(endpoint, selectedFile);
      onCompleted(result.management_code, "JSON 凭证已收下，当前状态为待审核。");
      setSelectedFile(null);
      await onCredentialCreated();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "上传失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <p className="section-tag">JSON</p>
        <h2>{title}</h2>
      </div>
      <p className="muted-copy">{intro}</p>
      <form className="stack-form" onSubmit={handleSubmit}>
        <label className="upload-drop">
          <span>{selectedFile ? selectedFile.name : "选择 Gemini JSON 凭证文件"}</span>
          <input
            accept=".json,application/json"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <button className="action-button" disabled={loading} type="submit">
          {loading ? "上传中..." : "上传 JSON 凭证"}
        </button>
      </form>
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}

