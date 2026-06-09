const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  return res;
}

/* ---------- Auth ---------- */
export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Login failed");
  return res.json();
}

export async function register(
  email: string,
  password: string,
  username: string,
) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, username }),
  });
  if (!res.ok)
    throw new Error((await res.json()).detail || "Registration failed");
  return res.json();
}

/* ---------- Conversations ---------- */
export async function listConversations() {
  const res = await apiFetch("/conversations");
  if (!res.ok) throw new Error("Failed to load conversations");
  return res.json();
}

export async function createConversation(title?: string) {
  const res = await apiFetch("/conversations", {
    method: "POST",
    body: JSON.stringify({ title: title || "New Conversation" }),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function deleteConversation(id: number) {
  const res = await apiFetch(`/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

export async function getConversationMessages(id: number) {
  const res = await apiFetch(`/conversations/${id}/messages?limit=200`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

/* ---------- Chat (SSE) ---------- */
export function chatStream(
  conversationId: number,
  query: string,
  onEvent: (data: any) => void,
  onDone: () => void,
  responseMode: string = "normal",
  responseLength: string = "standard",
) {
  const token = localStorage.getItem("token");
  const controller = new AbortController();

  fetch(`${API_BASE}/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query, response_mode: responseMode, response_length: responseLength }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        onEvent({ type: "error", content: "Failed to get response" });
        onDone();
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch {
              /* skip parse errors */
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onEvent({ type: "error", content: err.message });
        onDone();
      }
    });

  return () => controller.abort();
}

/* ---------- Documents ---------- */
export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiFetch("/documents/upload", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function chunkDocument(docId: number) {
  const res = await apiFetch(`/documents/${docId}/chunk`, {
    method: "POST",
    body: JSON.stringify({ chunk_size: 1000, chunk_overlap: 200 }),
  });
  if (!res.ok) throw new Error("Chunking failed");
  return res.json();
}

export async function embedDocument(docId: number) {
  const res = await apiFetch(`/documents/${docId}/embed`, {
    method: "POST",
    body: JSON.stringify({ provider: "huggingface" }),
  });
  if (!res.ok) throw new Error("Embedding failed");
  return res.json();
}

export async function listDocuments() {
  const res = await apiFetch("/documents");
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function deleteDocument(docId: number) {
  const res = await apiFetch(`/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete document");
}
