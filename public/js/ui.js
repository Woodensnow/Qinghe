const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.4-3.4"/>',
  pin: '<path d="M20 10c0 5.5-8 12-8 12S4 15.5 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.8"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  'arrow-right': '<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>',
  'arrow-left': '<path d="M20 12H5"/><path d="m11 6-6 6 6 6"/>',
  'arrow-up-right': '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
  'arrow-down': '<path d="M12 4v15"/><path d="m6 13 6 6 6-6"/>',
  upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8.5" cy="9" r="1.5"/><path d="m4 17 5-5 4 4 2-2 5 5"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="m6 7 1 14h10l1-14"/><path d="M10 11v6M14 11v6"/>',
  star: '<path d="m12 2.8 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.9-5.4 2.9 1-6L3.2 9.2l6.1-.9L12 2.8Z" fill="currentColor" stroke="none"/>',
  check: '<path d="m5 12 4.5 4.5L19 7"/>',
  shield: '<path d="M12 3 4.5 6v5.2c0 4.5 3.1 8.6 7.5 9.8 4.4-1.2 7.5-5.3 7.5-9.8V6L12 3Z"/><path d="m8.8 12 2.1 2.1 4.4-4.4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.4 2"/>',
  users: '<path d="M16 20v-1.8a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.2V20"/><circle cx="10" cy="7.5" r="3.5"/><path d="M20 20v-1.7a3.5 3.5 0 0 0-2.6-3.4M15.6 4.2a3.5 3.5 0 0 1 0 6.6"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18Z"/>',
  heart: '<path d="M20.8 5.9a5.1 5.1 0 0 0-7.2 0L12 7.5l-1.6-1.6a5.1 5.1 0 0 0-7.2 7.2L12 21l8.8-7.9a5.1 5.1 0 0 0 0-7.2Z"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4 3.3-6 7.5-6s6.7 2 7.5 6"/>',
  logout: '<path d="M9 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4"/><path d="m16 16 4-4-4-4"/><path d="M20 12H9"/>',
  camera: '<path d="M4 7h3l1.5-2h7L17 7h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1Z"/><circle cx="12" cy="13" r="4"/>',
  sparkles: '<path d="m12 3 1.7 4.8L18.5 9.5l-4.8 1.7L12 16l-1.7-4.8L5.5 9.5l4.8-1.7L12 3Z"/><path d="m19 15 .8 2.2 2.2.8-2.2.8L19 21l-.8-2.2-2.2-.8 2.2-.8L19 15Z"/>',
  landmark: '<path d="M3 10 12 4l9 6"/><path d="M5 10v8M9.7 10v8M14.3 10v8M19 10v8M3 21h18"/>',
  mask: '<path d="M3 9c3-2 6-2 9 0 3-2 6-2 9 0-1 5-3.8 7.5-6.2 6.3L12 14l-2.8 1.3C6.8 16.5 4 14 3 9Z"/><path d="M7 11h.01M17 11h.01"/>',
  walk: '<circle cx="13" cy="4.5" r="2"/><path d="m10 21 2-5-2-3 1-4 3 2 2.5 2"/><path d="M8 21h3M14 10l1.5 4 3 2"/>',
  food: '<path d="M7 3v8M4 3v4a3 3 0 0 0 6 0V3M7 11v10"/><path d="M17 3c-1.7 1.5-2.5 3.5-2.5 6.5 0 2.2 1 3.5 2.5 3.5v8M17 3v18"/>',
  car: '<path d="m5 12 1.7-4.4A2 2 0 0 1 8.6 6h6.8a2 2 0 0 1 1.9 1.6L19 12"/><rect x="3" y="12" width="18" height="6" rx="2"/><path d="M6 18v2M18 18v2M7 15h.01M17 15h.01"/>',
  child: '<circle cx="12" cy="7" r="3.5"/><path d="M5.5 21c.6-4.6 3.1-7 6.5-7s5.9 2.4 6.5 7"/><path d="M10.5 7h.01M13.5 7h.01M10.5 9c1 .7 2 .7 3 0"/>',
  route: '<circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M8 19h6a4 4 0 0 0 0-8H9a4 4 0 0 1 0-8h7"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.7 2.7L16.5 9"/>',
  quote: '<path d="M10 11H5V7a3 3 0 0 1 3-3M20 11h-5V7a3 3 0 0 1 3-3" fill="none"/><path d="M10 11H5v3a4 4 0 0 0 4 4M20 11h-5v3a4 4 0 0 0 4 4" fill="none"/><path d="M5 14c0 2.2 1.5 3.5 3.5 4M15 14c0 2.2 1.5 3.5 3.5 4"/>',
  map: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z"/><path d="M9 3v15M15 6v15"/>',
  wallet: '<rect x="3" y="6" width="18" height="14" rx="3"/><path d="M3 10h18M16 15h2"/>',
  leaf: '<path d="M20 4C10 5 4 10 4 17c6 .6 12-2 15-7 1-2 1-4 1-6Z"/><path d="M4 21c2-7 7-11 13-14"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 15v2"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
  'eye-off': '<path d="m3 3 18 18"/><path d="M10.6 6.1A10.9 10.9 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-2.8 3.5M6.6 6.6C3.9 8.4 2.5 12 2.5 12S6 18 12 18c1 0 1.9-.2 2.8-.5"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5h.01"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m16 8-2.2 6.3L8 16l2.2-6.3L16 8Z"/>',
  send: '<path d="m21 3-7.5 18-3.2-7.3L3 10.5 21 3Z"/><path d="M10.3 13.7 21 3"/>',
  message: '<path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z"/><path d="M8 11h8M8 15h5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  badge: '<path d="m12 2 2.3 1.7 2.8-.2 1 2.6 2.4 1.5-.6 2.8.6 2.8-2.4 1.5-1 2.6-2.8-.2L12 22l-2.3-1.7-2.8.2-1-2.6-2.4-1.5.6-2.8-.6-2.8 2.4-1.5 1-2.6 2.8.2L12 2Z"/><path d="m8.7 12 2.2 2.2 4.4-4.4"/>'
};

export const BRAND_MARK = `<svg class="brand-mark" viewBox="0 0 48 48" aria-hidden="true" fill="none"><path d="M39 9C21 11 10 20 9 34c13 1 24-5 29-13 2.2-4.2 1-9 1-12Z" fill="currentColor" opacity=".92"/><path d="M9 41c4-12 14-19 26-25" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>`;

export function icon(name, className = '') {
  const body = ICONS[name] || ICONS.info;
  return `<svg class="icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

export function escapeHTML(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function money(value) {
  const number = Number(value) || 0;
  return `¥${number.toLocaleString('zh-CN')}`;
}

export function avatar(name, tone = 'sage', size = 'md', url = '') {
  const safeTone = /^[a-z]+$/.test(tone) ? tone : 'sage';
  const initial = Array.from(String(name || '青'))[0]?.toUpperCase() || '青';
  const safeUrl = typeof url === 'string' && /^\/(?:uploads|assets)\//.test(url) ? url : '';
  const content = safeUrl
    ? `<img src="${escapeHTML(safeUrl)}" alt="" loading="lazy">`
    : escapeHTML(initial);
  return `<span class="avatar avatar--${size} avatar--${safeTone} ${safeUrl ? 'avatar--photo' : ''}" aria-hidden="true">${content}</span>`;
}

export function cityOptionsHTML(groups, selected = '', { allLabel = '' } = {}) {
  const all = allLabel ? `<option value="">${escapeHTML(allLabel)}</option>` : '';
  const grouped = (groups || [])
    .map(
      (group) =>
        `<optgroup label="${escapeHTML(group.region)}">${group.cities
          .map(
            (city) =>
              `<option value="${escapeHTML(city)}" ${city === selected ? 'selected' : ''}>${escapeHTML(city)}</option>`
          )
          .join('')}</optgroup>`
    )
    .join('');
  return all + grouped;
}

export function formatShortDate(dateString) {
  const [y, m, d] = String(dateString).split('-').map(Number);
  if (!y || !m || !d) return dateString;
  return `${m}/${String(d).padStart(2, '0')}`;
}

export function formatDateCN(dateString, { year = false } = {}) {
  const [y, m, d] = String(dateString).split('-').map(Number);
  if (!y || !m || !d) return dateString;
  return `${year ? `${y}年` : ''}${m}月${d}日`;
}

export function weekdayCN(dateString) {
  const [y, m, d] = String(dateString).split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()];
}

export function localDateISO(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(days) {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() + days);
  return d;
}

export function relativeDateLabel(dateString) {
  const today = localDateISO();
  if (dateString === today) return '今天';
  const tomorrow = localDateISO(addDays(1));
  if (dateString === tomorrow) return '明天';
  return weekdayCN(dateString);
}

export function joinedDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月加入`;
}

export function debounce(fn, wait = 180) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/* ---------------- Modal ---------------- */

let activeModal = null;

export function showModal(html, { className = '', showClose = true, closeOnBackdrop = true, onClose = null } = {}) {
  closeModal(true);
  const previouslyFocused = document.activeElement;
  const root = document.getElementById('modal-root');
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `
    <div class="modal ${className}" role="dialog" aria-modal="true">
      ${showClose ? '<button class="modal-close" type="button" data-modal-close aria-label="关闭">' + icon('close') + '</button>' : ''}
      ${html}
    </div>`;
  root.appendChild(backdrop);
  document.body.classList.add('modal-open');

  const dialog = backdrop.querySelector('.modal');
  let closed = false;

  const close = (immediate = false) => {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', onKeydown);
    backdrop.classList.remove('is-visible');
    document.body.classList.remove('modal-open');
    if (activeModal && activeModal.backdrop === backdrop) activeModal = null;
    const remove = () => {
      backdrop.remove();
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus({ preventScroll: true });
    };
    if (immediate) remove();
    else setTimeout(remove, 220);
    if (onClose) onClose();
  };

  const onKeydown = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusables = [...dialog.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')].filter(
      (el) => el.offsetParent !== null
    );
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop && closeOnBackdrop) close();
    if (event.target.closest('[data-modal-close]')) close();
  });
  document.addEventListener('keydown', onKeydown);

  requestAnimationFrame(() => {
    backdrop.classList.add('is-visible');
    const focusTarget =
      dialog.querySelector('[autofocus]') ||
      dialog.querySelector('input:not([type="hidden"]):not([type="checkbox"]), select, textarea') ||
      dialog.querySelector('button, a[href]');
    if (focusTarget) focusTarget.focus({ preventScroll: true });
  });

  activeModal = { backdrop, dialog, close };
  return { backdrop, dialog, close };
}

export function closeModal(immediate = false) {
  if (activeModal) {
    const modal = activeModal;
    activeModal = null;
    modal.close(immediate);
  }
}

export function isModalOpen() {
  return Boolean(activeModal);
}

export function confirmDialog({ title, message, confirmText = '确认', cancelText = '再想想', danger = false }) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };
    const modal = showModal(
      `<div class="confirm-dialog">
        <div class="confirm-icon ${danger ? 'is-danger' : ''}">${icon(danger ? 'alert' : 'info')}</div>
        <h2>${escapeHTML(title)}</h2>
        <p>${escapeHTML(message)}</p>
        <div class="confirm-actions">
          <button type="button" class="btn btn--ghost" data-confirm-cancel>${escapeHTML(cancelText)}</button>
          <button type="button" class="btn ${danger ? 'btn--danger' : 'btn--primary'}" data-confirm-ok>${escapeHTML(confirmText)}</button>
        </div>
      </div>`,
      {
        className: 'modal--confirm',
        showClose: false,
        onClose: () => finish(false)
      }
    );
    modal.dialog.querySelector('[data-confirm-cancel]').addEventListener('click', () => {
      finish(false);
      modal.close();
    });
    modal.dialog.querySelector('[data-confirm-ok]').addEventListener('click', () => {
      finish(true);
      modal.close();
    });
  });
}

/* ---------------- Toast ---------------- */

export function toast(message, type = 'success') {
  const root = document.getElementById('toast-root');
  const item = document.createElement('div');
  item.className = `toast toast--${type}`;
  item.innerHTML = `<span class="toast-icon">${icon(type === 'error' ? 'alert' : type === 'info' ? 'info' : 'check-circle')}</span><span>${escapeHTML(message)}</span>`;
  root.appendChild(item);
  requestAnimationFrame(() => item.classList.add('is-visible'));
  setTimeout(() => {
    item.classList.remove('is-visible');
    setTimeout(() => item.remove(), 260);
  }, 3000);
}

/* ---------------- Favorites ---------------- */

const FAVORITES_KEY = 'qinghe_favorites';

export function getFavorites() {
  try {
    const value = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function isFavorite(id) {
  return getFavorites().includes(id);
}

export function toggleFavorite(id) {
  const favorites = getFavorites();
  const has = favorites.includes(id);
  const next = has ? favorites.filter((item) => item !== id) : [...favorites, id];
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
  } catch {
    /* noop */
  }
  return !has;
}

/* ---------------- Reveal ---------------- */

export function initReveals(root = document) {
  const items = [...root.querySelectorAll('.reveal:not(.is-observed)')];
  if (!items.length) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -40px' }
  );
  items.forEach((item, index) => {
    item.style.setProperty('--reveal-delay', `${Math.min(index * 55, 330)}ms`);
    item.classList.add('is-observed');
    observer.observe(item);
  });
}

export function setPageTitle(title) {
  document.title = title ? `${title} · 青禾` : '青禾 · 城市轻兼职';
}

export function showComingSoon(track) {
  const name = track?.name || '这个';
  showModal(
    `<div class="coming-soon-modal">
      <span class="eyebrow">COMING SOON</span>
      <div class="coming-soon-icon">${icon(track?.icon || 'sparkles')}</div>
      <h2>${escapeHTML(name)}板块正在生长</h2>
      <p>我们想先把「地陪」这一件事做扎实，再慢慢把摄影、模特、博物馆讲解和 NPC 带到你面前。</p>
      <div class="coming-soon-actions">
        <a class="btn btn--primary" href="/guides">先去看看地陪 ${icon('arrow-right')}</a>
        <button class="btn btn--ghost" type="button" data-modal-close>留个期待</button>
      </div>
      <span class="coming-soon-note">${icon('leaf')} 好服务，值得慢慢长出来</span>
    </div>`,
    { className: 'modal--narrow' }
  );
}
