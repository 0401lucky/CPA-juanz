import { FormEvent, useState } from "react";

import { finalizeGeminiOAuth, startGeminiOAuth } from "../lib/api";


type GeminiOauthCardProps = {
  endpoint: "/public/oauth/gemini/start" | "/me/credentials/oauth/gemini/start";
  title: string;
  intro: string;
  onCompleted: (managementCode: string | null, notice: string) => void;
  onCredentialCreated: () => Promise<void> | void;
};

export function GeminiOauthCard({
  endpoint,
  title,
  intro,
  onCompleted,
  onCredentialCreated
}: GeminiOauthCardProps) {
  const [projectId, setProjectId] = useState("GOOGLE_ONE");
  const [flowId, setFlowId] = useState<string | null>(null);
  const [redirectUrl, setRedirectUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await startGeminiOAuth(endpoint, projectId);
      setFlowId(result.flow_id);
      window.open(result.auth_url, "_blank", "noopener,noreferrer");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "启动授权失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalize() {
    if (!flowId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await finalizeGeminiOAuth(flowId, redirectUrl.trim() || undefined);
      onCompleted(
        result.management_code,
        "OAuth 凭证已抓取成功，当前状态为待审核。"
      );
      setFlowId(null);
      setRedirectUrl("");
      await onCredentialCreated();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "完成授权失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel accent-panel">
      <div className="panel-header">
        <p className="section-tag">OAuth</p>
        <h2>{title}</h2>
      </div>
      <p className="muted-copy">{intro}</p>
      <form className="stack-form" onSubmit={handleStart}>
        <label className="field">
          <span>Project ID / 模式</span>
          <input
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            placeholder="GOOGLE_ONE"
          />
        </label>
        <button className="action-button action-button-dark" disabled={loading} type="submit">
          {loading ? "处理中..." : "Google 授权捐献"}
        </button>
      </form>
      {flowId ? (
        <div className="oauth-finish-box">
          <p>授权页已打开。完成 Google 授权后，回到这里点击“我已完成授权”。</p>
          <label className="field">
            <span>如果自动回跳失败，可手动粘贴回调 URL</span>
            <textarea
              rows={3}
              value={redirectUrl}
              onChange={(event) => setRedirectUrl(event.target.value)}
              placeholder="https://your-app/callback?code=...&state=..."
            />
          </label>
          <button className="action-button" disabled={loading} onClick={handleFinalize} type="button">
            我已完成授权
          </button>
        </div>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}

