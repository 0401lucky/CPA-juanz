import { useEffect, useState } from "react";

import { CredentialTable } from "../components/CredentialTable";
import {
  Credential,
  adminListCredentials,
  adminLogin,
  adminPublishCredential,
  adminRejectCredential
} from "../lib/api";


export function AdminPage() {
  const [password, setPassword] = useState("");
  const [items, setItems] = useState<Credential[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reasonDrafts, setReasonDrafts] = useState<Record<string, string>>({});

  async function refresh() {
    try {
      const result = await adminListCredentials();
      setItems(result);
      setError("");
    } catch (caughtError) {
      setItems([]);
      setError(caughtError instanceof Error ? caughtError.message : "加载失败");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleLogin() {
    try {
      await adminLogin(password);
      setNotice("管理员会话已建立。");
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "登录失败");
    }
  }

  async function handlePublish(credentialId: string) {
    try {
      await adminPublishCredential(credentialId);
      setNotice("已发布到外部 CPA。");
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "发布失败");
    }
  }

  async function handleReject(credentialId: string) {
    try {
      await adminRejectCredential(
        credentialId,
        reasonDrafts[credentialId] || "不符合当前捐献规则"
      );
      setNotice("已驳回该条凭证。");
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "驳回失败");
    }
  }

  return (
    <div className="page-grid">
      <section className="panel admin-banner">
        <div className="panel-header">
          <p className="section-tag">Back Office</p>
          <h2>审核工作台</h2>
        </div>
        <p className="muted-copy">
          这里负责把公开捐献入口收进来的 Gemini 凭证做审核、发布和驳回。发布成功后，才会真正写入 Zeabur 上的外部 CPA。
        </p>
        <div className="inline-form">
          <input
            onChange={(event) => setPassword(event.target.value)}
            placeholder="输入管理员密码"
            type="password"
            value={password}
          />
          <button className="action-button action-button-dark" onClick={handleLogin} type="button">
            登录后台
          </button>
        </div>
        {notice ? <p className="notice-text">{notice}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <CredentialTable
        emptyText="待审核队列当前为空。"
        items={items.filter((item) =>
          ["pending_review", "duplicate_blocked", "publish_failed"].includes(item.status)
        )}
        title="待审核队列"
        actions={(item) => (
          <div className="action-stack">
            <button className="mini-button" onClick={() => void handlePublish(item.id)} type="button">
              发布
            </button>
            <input
              className="mini-input"
              onChange={(event) =>
                setReasonDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value
                }))
              }
              placeholder="驳回原因"
              value={reasonDrafts[item.id] ?? ""}
            />
            <button className="mini-button mini-button-danger" onClick={() => void handleReject(item.id)} type="button">
              驳回
            </button>
          </div>
        )}
      />

      <CredentialTable
        emptyText="还没有已发布记录。"
        items={items.filter((item) => item.status === "published")}
        title="已发布记录"
      />
    </div>
  );
}

