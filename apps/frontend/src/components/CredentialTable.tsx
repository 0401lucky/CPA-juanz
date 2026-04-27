import type { Credential } from "../lib/api";


type CredentialTableProps = {
  title: string;
  items: Credential[];
  emptyText: string;
  actions?: (item: Credential) => React.ReactNode;
};

const statusMap: Record<string, string> = {
  pending_review: "待审核",
  duplicate_blocked: "重复拦截",
  published: "已发布",
  rejected: "已驳回",
  deleted: "已删除",
  delete_failed: "删除失败",
  publish_failed: "发布失败"
};

export function CredentialTable({
  title,
  items,
  emptyText,
  actions
}: CredentialTableProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <p className="section-tag">Records</p>
        <h2>{title}</h2>
      </div>
      {items.length === 0 ? (
        <p className="muted-copy">{emptyText}</p>
      ) : (
        <div className="table-wrap">
          <table className="credential-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>状态</th>
                <th>账号</th>
                <th>Project</th>
                <th>备注</th>
                {actions ? <th>操作</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.display_name}</td>
                  <td>
                    <span className={`status-pill status-${item.status}`}>
                      {statusMap[item.status] ?? item.status}
                    </span>
                  </td>
                  <td>{item.parsed_email ?? "未解析"}</td>
                  <td>{item.parsed_project_id ?? "未解析"}</td>
                  <td>{item.rejection_reason ?? item.error_message ?? "—"}</td>
                  {actions ? <td>{actions(item)}</td> : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

