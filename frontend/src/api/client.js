const API_ROOT = import.meta.env.VITE_API_URL || '';
const BASE = `${API_ROOT}/api`;

function getToken() {
  return localStorage.getItem('argus_token');
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : null;
  if (!res.ok) {
    throw new Error(data?.error || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
  register: (name, email, password) => request('/auth/register', { method: 'POST', body: { name, email, password }, auth: false }),
  me: () => request('/auth/me'),

  listCameras: () => request('/cameras'),
  getCamera: (id) => request(`/cameras/${id}`),
  createCamera: (data) => request('/cameras', { method: 'POST', body: data }),
  updateCamera: (id, patch) => request(`/cameras/${id}`, { method: 'PATCH', body: patch }),
  deleteCamera: (id) => request(`/cameras/${id}`, { method: 'DELETE' }),
  toggleCamera: (id) => request(`/cameras/${id}/toggle`, { method: 'POST' }),

  listAlerts: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/alerts${qs ? `?${qs}` : ''}`);
  },
  getAlert: (id) => request(`/alerts/${id}`),
  updateAlertStatus: (id, status) => request(`/alerts/${id}`, { method: 'PATCH', body: { status } }),
};

export function saveToken(token) {
  localStorage.setItem('argus_token', token);
}

export function clearToken() {
  localStorage.removeItem('argus_token');
}

export { getToken, API_ROOT };
