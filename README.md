# CPA Gemini 捐献站

一个独立于 CPA 本体的前后端站点，用来接收公开用户捐献的 Gemini CLI 凭证，再由管理员审核后发布到你已经部署在 Zeabur 的外部 CPA。

## 功能

- 公开用户支持两种入口：
  - Gemini OAuth 捐献
  - 上传本地 Gemini JSON 凭证
- 第一次成功提交后返回管理码
- 用户凭管理码查看、继续追加、删除自己的凭证
- 所有提交先进入待审核
- 管理员审核通过后，后端才会把凭证发布到外部 CPA
- 删除已发布凭证时，后端会同步调用外部 CPA 删除真实 `auth-file`
- 写入 CPA 时统一使用固定前缀，避免碰到你现有的其它凭证

## 目录

- `apps/backend`：FastAPI + SQLite 后端
- `apps/frontend`：React + Vite 前端
- `infra/Caddyfile`：单域名反向代理
- `docker-compose.yml`：站点自身的一键部署编排

## 外部 CPA 要求

你的 Zeabur CPA 必须已经开启并可从站点后端访问以下管理能力：

- `GET /v0/management/auth-files`
- `POST /v0/management/auth-files`
- `DELETE /v0/management/auth-files`
- `GET /v0/management/gemini-cli-auth-url`
- `POST /v0/management/oauth-callback`
- `GET /v0/management/get-auth-status`

同时需要准备一个管理密钥，并允许远程管理。

## 本地开发

### 1. 后端测试

```bash
npm run test:backend
```

### 2. 前端安装与测试

```bash
npm run install:frontend
npm run test:frontend
```

### 3. 前端构建与检查

```bash
npm run lint:frontend
npm run build:frontend
```

### 4. 一键检查

```bash
npm run check
```

## Docker Compose 启动

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 填好 `.env` 里的外部 CPA 地址、管理密钥、管理员密码和会话密钥。

3. 启动：

```bash
docker compose up --build
```

默认入口：

- 站点首页：`http://localhost:8080/`
- 公开捐献：`/`
- 我的凭证：`/my`
- 审核后台：`/admin`

## 重要说明

- OAuth 捐献成功后，站点会先从外部 CPA 抓取刚生成的 Gemini 凭证，再从 CPA 临时删除，放入本站待审核池；只有管理员发布后才会重新写回 CPA。
- `CPA_AUTH_FILE_PREFIX` 默认是 `donate-geminicli`，本站只处理这个前缀下的发布文件，不会主动碰你外部 CPA 原有的其它凭证。
- 管理码只展示一次，后端只保存哈希，不支持找回。
