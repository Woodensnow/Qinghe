import { api, clearToken, getToken, setToken } from './api.js?v=1.7.0';

export const session = {
  user: null,
  ready: false
};

export function applySession(token, user) {
  setToken(token);
  session.user = user;
  session.ready = true;
  window.dispatchEvent(new CustomEvent('session:change', { detail: { user } }));
}

export function updateSessionUser(user) {
  session.user = user;
  session.ready = true;
  window.dispatchEvent(new CustomEvent('session:change', { detail: { user } }));
}

export async function bootSession() {
  if (!getToken()) {
    session.ready = true;
    return null;
  }
  try {
    const { user } = await api('/api/auth/me');
    session.user = user;
  } catch {
    clearToken();
    session.user = null;
  }
  session.ready = true;
  return session.user;
}

export async function signOut() {
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } catch {
    /* 本地会话仍然清除 */
  }
  clearToken();
  session.user = null;
  window.dispatchEvent(new CustomEvent('session:change', { detail: { user: null } }));
}
