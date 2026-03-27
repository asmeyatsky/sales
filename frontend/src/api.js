const API_KEY_STORAGE = 'scout_api_key';

export function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE) || '';
}

export function setApiKey(key) {
  localStorage.setItem(API_KEY_STORAGE, key);
}

async function request(method, path, body = null, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v != null) url.searchParams.set(k, v);
  });

  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': getApiKey(),
    },
  };

  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(url.toString(), opts);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  get: (path, params) => request('GET', path, null, params),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  getPaginated: (path, offset = 0, limit = 25, extraParams = {}) =>
    request('GET', path, null, { offset, limit, ...extraParams }),
};
