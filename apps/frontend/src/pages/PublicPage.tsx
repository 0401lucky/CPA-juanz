import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { GeminiOauthCard } from "../components/GeminiOauthCard";
import { JsonUploadCard } from "../components/JsonUploadCard";
import { loginWithManagementCode } from "../lib/api";


export function PublicPage() {
  const [managementCode, setManagementCode] = useState("");
  const [issuedCode, setIssuedCode] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  function handleCompleted(code: string | null, nextNotice: string) {
    setNotice(nextNotice);
    if (code) {
      setIssuedCode(code);
    }
  }

  async function handleManagementCodeLogin() {
    setError("");
    try {
      await loginWithManagementCode(managementCode);
      navigate("/my");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "管理码登录失败");
    }
  }

  return (
    <div className="page-grid page-grid-home">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow eyebrow-ink">Public Relay</p>
          <h2>Gemini 凭证捐献站</h2>
          <p>
            这是一个接在外部 CPA 之上的公开捐献入口。你可以上传 Gemini
            JSON，或直接走 Google 授权，把凭证交给审核池，发布后才会进入外部 CPA。
          </p>
        </div>
        <div className="feature-band">
          <div>
            <strong>公开入口</strong>
            <span>任何人都能发起捐献</span>
          </div>
          <div>
            <strong>审核发布</strong>
            <span>不会直接写进线上配额池</span>
          </div>
          <div>
            <strong>管理码</strong>
            <span>用户自行查看、追加、删除</span>
          </div>
        </div>
        {notice ? <p className="notice-text">{notice}</p> : null}
        {issuedCode ? (
          <div className="code-vault">
            <p className="section-tag">你的管理码</p>
            <strong>{issuedCode}</strong>
            <span>请保存这串管理码。后续查看、继续上传、删除自己的凭证都靠它。</span>
          </div>
        ) : null}
      </section>

      <GeminiOauthCard
        endpoint="/public/oauth/gemini/start"
        intro="适合直接用 Google 账号授权捐献。默认支持 GOOGLE_ONE，也可以改成指定 Project ID。"
        onCompleted={handleCompleted}
        onCredentialCreated={() => Promise.resolve()}
        title="Google 授权捐献"
      />

      <JsonUploadCard
        endpoint="/public/credentials/json"
        intro="如果你本地已经有 Gemini CLI 凭证 JSON，可以直接上传进审核池。"
        onCompleted={handleCompleted}
        onCredentialCreated={() => Promise.resolve()}
        title="上传 JSON 凭证"
      />

      <section className="panel code-panel">
        <div className="panel-header">
          <p className="section-tag">Management Code</p>
          <h2>输入管理码</h2>
        </div>
        <p className="muted-copy">
          第一次成功上传后，你会得到一串管理码。用它进入“我的凭证”，继续追加或删除自己名下的记录。
        </p>
        <div className="stack-form">
          <label className="field">
            <span>管理码</span>
            <input
              onChange={(event) => setManagementCode(event.target.value)}
              placeholder="粘贴你的管理码"
              value={managementCode}
            />
          </label>
          <button className="action-button action-button-dark" onClick={handleManagementCodeLogin} type="button">
            进入我的凭证
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </div>
  );
}

