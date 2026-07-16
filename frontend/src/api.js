// Tiny fetch wrapper around the backend API (proxied via Vite to :8000).
const BASE = "/api/v1";
const TOKEN_KEY = "aisp_token";

// --- Auth token helpers (persisted in localStorage) ---
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
}
function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) {
    // Session missing/expired — drop the token and tell the app to show login.
    clearToken();
    window.dispatchEvent(new Event("auth:logout"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.error?.message || detail;
    } catch {
      /* ignore non-JSON errors */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- Auth ---
  login: async (username, password) => {
    const res = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setToken(res.access_token);
    return res;
  },
  me: () => request("/auth/me"),
  logout: () => {
    clearToken();
    window.dispatchEvent(new Event("auth:logout"));
  },

  systemInfo: () => request("/system/info"),
  outbox: () => request("/system/outbox"),

  dashboard: () => request("/stats/dashboard"),

  sendMessage: (payload) =>
    request("/chat/send", { method: "POST", body: JSON.stringify(payload) }),
  sendPhoto: (payload) =>
    request("/chat/photo", { method: "POST", body: JSON.stringify(payload) }),
  runAutomation: (count = 5) =>
    request(`/automation/run?count=${count}`, { method: "POST" }),

  conversations: (status) =>
    request(`/conversations${status ? `?status=${status}` : ""}`),
  conversation: (id) => request(`/conversations/${id}`),
  agentReply: (id, content) =>
    request(`/conversations/${id}/reply`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  setConversationStatus: (id, status) =>
    request(`/conversations/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  orders: (limit = 1500) => request(`/orders?limit=${limit}`),
  orderCount: () => request("/orders/meta/count"),
  demoIdentities: () => request("/customers/with-orders?limit=8"),
  activity: (limit = 12) => request(`/orders/events/recent?limit=${limit}`),
  pendingRefunds: () => request("/orders/refunds/pending"),
  completeRefund: (orderNumber) =>
    request(`/orders/${orderNumber}/refund/complete`, { method: "POST" }),

  faqs: () => request("/faqs"),
  faqSuggestions: () => request("/faqs/suggestions"),
  approveSuggestion: (id, payload) =>
    request(`/faqs/suggestions/${id}/approve`, { method: "POST", body: JSON.stringify(payload) }),
  dismissSuggestion: (id) =>
    request(`/faqs/suggestions/${id}/dismiss`, { method: "POST" }),
  createFaq: (payload) =>
    request("/faqs", { method: "POST", body: JSON.stringify(payload) }),
  updateFaq: (id, payload) =>
    request(`/faqs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteFaq: (id) => request(`/faqs/${id}`, { method: "DELETE" }),
};
