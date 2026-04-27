export type Credential = {
  id: string;
  source_type: "json" | "oauth";
  display_name: string;
  status: string;
  cpa_file_name: string | null;
  rejection_reason: string | null;
  error_message: string | null;
  parsed_email: string | null;
  parsed_project_id: string | null;
  created_at: string;
  updated_at: string;
};

type JsonUploadResponse = {
  management_code: string | null;
  credential: Credential;
};

type OAuthStartResponse = {
  flow_id: string;
  auth_url: string;
};

type OAuthFinalizeResponse = {
  management_code: string | null;
  credential: Credential;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(data.detail ?? "请求失败");
  }
  return response.json() as Promise<T>;
}

export async function uploadCredential(
  endpoint: string,
  file: File
): Promise<JsonUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData,
    credentials: "include"
  });
  return parseResponse<JsonUploadResponse>(response);
}

export async function startGeminiOAuth(
  endpoint: string,
  projectId: string
): Promise<OAuthStartResponse> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      project_id: projectId
    })
  });
  return parseResponse<OAuthStartResponse>(response);
}

export async function finalizeGeminiOAuth(
  flowId: string,
  redirectUrl?: string
): Promise<OAuthFinalizeResponse> {
  const response = await fetch(`${API_BASE_URL}/public/oauth/gemini/callback-relay`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      flow_id: flowId,
      redirect_url: redirectUrl || undefined
    })
  });
  return parseResponse<OAuthFinalizeResponse>(response);
}

export async function loginWithManagementCode(managementCode: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/public/management-code/session`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      management_code: managementCode
    })
  });
  await parseResponse<{ status: string }>(response);
}

export async function listMyCredentials(): Promise<Credential[]> {
  const response = await fetch(`${API_BASE_URL}/me/credentials`, {
    credentials: "include"
  });
  const data = await parseResponse<{ items: Credential[] }>(response);
  return data.items;
}

export async function deleteMyCredential(credentialId: string): Promise<Credential> {
  const response = await fetch(`${API_BASE_URL}/me/credentials/${credentialId}`, {
    method: "DELETE",
    credentials: "include"
  });
  const data = await parseResponse<{ credential: Credential }>(response);
  return data.credential;
}

export async function adminLogin(password: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/admin/session`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ password })
  });
  await parseResponse<{ status: string }>(response);
}

export async function adminListCredentials(status?: string): Promise<Credential[]> {
  const url = new URL(`${API_BASE_URL}/admin/credentials`, window.location.origin);
  if (status) {
    url.searchParams.set("status", status);
  }
  const response = await fetch(url.pathname + url.search, {
    credentials: "include"
  });
  const data = await parseResponse<{ items: Credential[] }>(response);
  return data.items;
}

export async function adminPublishCredential(credentialId: string): Promise<Credential> {
  const response = await fetch(`${API_BASE_URL}/admin/credentials/${credentialId}/publish`, {
    method: "POST",
    credentials: "include"
  });
  const data = await parseResponse<{ credential: Credential }>(response);
  return data.credential;
}

export async function adminRejectCredential(
  credentialId: string,
  reason: string
): Promise<Credential> {
  const response = await fetch(`${API_BASE_URL}/admin/credentials/${credentialId}/reject`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ reason })
  });
  const data = await parseResponse<{ credential: Credential }>(response);
  return data.credential;
}

