let renderHandler = null;

export function parseRoute() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  const search = new URLSearchParams(window.location.search);

  if (path === '/') return { name: 'home', params: {}, search };
  if (path === '/guides') return { name: 'guides', params: {}, search };
  if (path === '/become') return { name: 'become', params: {}, search };
  if (path === '/account') return { name: 'account', params: {}, search };
  if (path === '/profile') return { name: 'profile', params: {}, search };
  if (path === '/messages') return { name: 'messages', params: {}, search };
  if (path === '/matching') return { name: 'matching', params: {}, search };

  const guide = path.match(/^\/guides\/([^/]+)$/);
  if (guide) return { name: 'guide', params: { id: decodeURIComponent(guide[1]) }, search };

  return { name: 'notfound', params: {}, search };
}

export function currentUrl() {
  return window.location.pathname + window.location.search;
}

export function navigate(to, { replace = false, scroll = true } = {}) {
  const target = to.startsWith('/') ? to : `/${to}`;
  if (replace) history.replaceState({}, '', target);
  else history.pushState({}, '', target);
  if (scroll) window.scrollTo({ top: 0, behavior: 'auto' });
  if (renderHandler) renderHandler();
  window.dispatchEvent(new CustomEvent('route:change'));
}

export function replaceUrl(to) {
  const target = to.startsWith('/') ? to : `/${to}`;
  history.replaceState({}, '', target);
}

export function startRouter(handler) {
  renderHandler = handler;

  window.addEventListener('popstate', () => {
    if (renderHandler) renderHandler();
    window.scrollTo({ top: 0, behavior: 'auto' });
    window.dispatchEvent(new CustomEvent('route:change'));
  });

  document.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest('a[href]');
    if (!anchor) return;
    const href = anchor.getAttribute('href');
    if (!href || !href.startsWith('/') || anchor.target === '_blank' || anchor.hasAttribute('download')) return;
    if (anchor.dataset.native === 'true') return;
    event.preventDefault();
    if (currentUrl() !== href) navigate(href);
  });
}
