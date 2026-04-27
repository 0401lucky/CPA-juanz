import { useEffect, useState } from "react";

import { CredentialTable } from "../components/CredentialTable";
import { GeminiOauthCard } from "../components/GeminiOauthCard";
import { JsonUploadCard } from "../components/JsonUploadCard";
import {
  Credential,
  deleteMyCredential,
  listMyCredentials,
  loginWithManagementCode
} from "../lib/api";


export function MyCredentialsPage() {
  const [items, setItems] = useState<Credential[]>([]);
  const [managementCode, setManagementCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      setLoading(true);
      const result = await listMyCredentials();
      setItems(result);
      setError("");
    } catch (caughtError) {
      setItems([]);
      setError(caughtError instanceof Error ? caughtError.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleManagementCodeLogin() {
    try {
      await loginWithManagementCode(managementCode);
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "管理码登录失败");
    }
  }

  async function handleDelete(credentialId: string) {
    try {
      await deleteMyCredential(credentialId);
      setNotice("已提交删除，若记录已发布，后端会同步从外部 CPA 下线。");
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "删除失败");
    }
  }

  function handleCompleted(code: string | null, nextNotice: string) {
    if (code) {
      setNotice(`新管理码：${code}`);
    } else {
      setNotice(nextNotice);
    }
  }

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <p className="section-tag">Personal Vault</p>
          <h2>我的凭证</h2>
        </div>
        <p className="muted-copy">
          如果你还没建立会话，在这里输入管理码；如果已经有 Cookie，会自动拉取你的名下记录。
        </p>
        <div className="inline-form">
          <input
            onChange={(event) => setManagementCode(event.target.value)}
            placeholder="输入管理码"
            value={managementCode}
          />
          <button className="action-button action-button-dark" onClick={handleManagementCodeLogin} type="button">
            登录
          </button>
        </div>
        {notice ? <p className="notice-text">{notice}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <GeminiOauthCard
        endpoint="/me/credentials/oauth/gemini/start"
        intro="已经登录管理码后，可继续把新的 Gemini OAuth 凭证归到同一个捐献者名下。"
        onCompleted={handleCompleted}
        onCredentialCreated={refresh}
        title="继续追加 Gemini 凭证"
      />

      <JsonUploadCard
        endpoint="/me/credentials/json"
        intro="把你已有的 Gemini JSON 凭证继续追加进同一个管理码账户。"
        onCompleted={handleCompleted}
        onCredentialCreated={refresh}
        title="继续追加 JSON 凭证"
      />

      <CredentialTable
        emptyText={loading ? "正在加载..." : "当前还没有记录。"}
        items={items}
        title="当前记录"
        actions={(item) => (
          <button className="mini-button" onClick={() => void handleDelete(item.id)} type="button">
            删除
          </button>
        )}
      />
    </div>
  );
}

