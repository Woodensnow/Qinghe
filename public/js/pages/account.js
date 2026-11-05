import { api, ApiError } from '../api.js?v=1.7.0';
import { openAuthModal } from '../components/auth-modal.js?v=1.7.0';
import { navigate, replaceUrl } from '../router.js?v=1.7.0';
import { session, signOut } from '../session.js?v=1.7.0';
import {
  avatar,
  confirmDialog,
  escapeHTML,
  formatDateCN,
  icon,
  initReveals,
  joinedDate,
  money,
  setPageTitle,
  toast
} from '../ui.js?v=1.7.0';

const STATUS_MAP = {
  pending: { label: '待地陪确认', className: 'pending', icon: 'clock' },
  confirmed: { label: '已确认', className: 'confirmed', icon: 'check-circle' },
  completed: { label: '已完成', className: 'completed', icon: 'check' },
  cancelled: { label: '已取消', className: 'cancelled', icon: 'close' }
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 6) return '夜深了';
  if (hour < 11) return '早上好';
  if (hour < 14) return '中午好';
  if (hour < 18) return '下午好';
  return '晚上好';
}

function gateShell() {
  return `
    <section class="account-gate">
      <div class="account-gate-card">
        <div class="account-gate-visual">
          <span class="gate-mark">${icon('user')}</span>
          <span class="account-gate-line"></span>
          <span class="account-gate-route">${icon('route')}</span>
        </div>
        <div>
          <span class="eyebrow">YOUR QINGHE</span>
          <h1>登录后，看看你的<br>城市日程。</h1>
          <p>预约记录、发布的服务和接下来的见面，都会安静地待在这里。</p>
          <button type="button" class="btn btn--primary btn--lg" data-account-login>登录 / 注册 ${icon('arrow-right')}</button>
          <div class="gate-benefits">
            <span>${icon('calendar')} 管理预约</span>
            <span>${icon('route')} 管理服务</span>
            <span>${icon('shield')} 平台保障</span>
          </div>
        </div>
      </div>
    </section>`;
}

function bookingItem(booking) {
  const status = STATUS_MAP[booking.status] || STATUS_MAP.pending;
  const active = ['pending', 'confirmed'].includes(booking.status);
  return `
    <article class="booking-item" data-booking="${escapeHTML(booking.id)}">
      <a class="booking-cover" href="/guides/${encodeURIComponent(booking.guideId)}">
        <img src="${escapeHTML(booking.guideCover)}" alt="${escapeHTML(booking.guideName)}" loading="lazy">
      </a>
      <div class="booking-info">
        <div class="booking-title-row">
          <div>
            <span class="booking-city">${icon('pin')} ${escapeHTML(booking.guideCity)}</span>
            <h3><a href="/guides/${encodeURIComponent(booking.guideId)}">${escapeHTML(booking.guideName)}</a></h3>
          </div>
          <span class="status-pill status-pill--${status.className}">${icon(status.icon)} ${status.label}</span>
        </div>
        <p class="booking-package">${escapeHTML(booking.packageName)} · ${escapeHTML(booking.packageDuration)} · ${booking.people} 人</p>
        <div class="booking-meta">
          <span>${icon('calendar')} ${formatDateCN(booking.date, { year: true })}</span>
          <span>${icon('clock')} ${escapeHTML(booking.time)} 开始</span>
          <span>${icon('wallet')} ${money(booking.total)}</span>
        </div>
        ${booking.note ? `<p class="booking-note-text">${icon('message')} ${escapeHTML(booking.note)}</p>` : ''}
      </div>
      <div class="booking-actions">
        <a class="btn btn--ghost btn--sm" href="/guides/${encodeURIComponent(booking.guideId)}">查看地陪</a>
        ${
          active
            ? `<button type="button" class="btn btn--text btn--sm booking-cancel" data-cancel="${escapeHTML(booking.id)}">取消预约</button>`
            : booking.status === 'cancelled'
              ? `<a class="btn btn--text btn--sm" href="/guides/${encodeURIComponent(booking.guideId)}">再次预约</a>`
              : ''
        }
      </div>
    </article>`;
}

function bookingsPanel(bookings) {
  if (!bookings.length) {
    return `<div class="empty-state empty-state--account">
      <span class="empty-icon">${icon('calendar')}</span>
      <span class="eyebrow">NO PLANS YET</span>
      <h3>还没有安排下一次见面</h3>
      <p>去「找地陪」看看，把某个周末交给一条没走过的小路。</p>
      <a class="btn btn--primary" href="/guides">去寻找地陪 ${icon('arrow-right')}</a>
    </div>`;
  }
  return `<div class="booking-list">${bookings.map(bookingItem).join('')}</div>`;
}

function serviceItem(guide) {
  const published = guide.status === 'published';
  return `
    <article class="manage-service" data-service="${escapeHTML(guide.id)}">
      <a class="manage-cover" href="/guides/${encodeURIComponent(guide.id)}">
        <img src="${escapeHTML(guide.cover)}" alt="${escapeHTML(guide.name)}" loading="lazy">
        <span class="manage-status ${published ? 'is-live' : 'is-paused'}"><i></i>${published ? '接单中' : '已暂停'}</span>
      </a>
      <div class="manage-body">
        <span class="manage-city">${icon('pin')} ${escapeHTML(guide.city)}</span>
        <h3><a href="/guides/${encodeURIComponent(guide.id)}">${escapeHTML(guide.headline)}</a></h3>
        <div class="manage-meta">
          <span>${money(guide.price)} / 半天起</span>
          <span>${icon('star')} ${guide.reviewCount ? `${Number(guide.rating).toFixed(1)}（${guide.reviewCount}）` : '暂无评价'}</span>
          <span>${Number(guide.orders) || 0} 次陪伴</span>
        </div>
        <div class="manage-actions">
          <a class="btn btn--ghost btn--sm" href="/guides/${encodeURIComponent(guide.id)}">查看页面</a>
          <button type="button" class="switch ${published ? 'is-on' : ''}" data-toggle-service="${escapeHTML(guide.id)}" role="switch" aria-checked="${published}" aria-label="${published ? '暂停接单' : '恢复接单'}">
            <span class="switch-track"><span class="switch-thumb"></span></span>
            <span>${published ? '暂停接单' : '恢复接单'}</span>
          </button>
        </div>
      </div>
    </article>`;
}

function servicesPanel(guides) {
  if (!guides.length) {
    return `<div class="empty-state empty-state--account">
      <span class="empty-icon">${icon('route')}</span>
      <span class="eyebrow">NO SERVICE YET</span>
      <h3>还没有发布地陪服务</h3>
      <p>你最熟悉的城市角落，也许正是别人想找的那条路线。</p>
      <a class="btn btn--primary" href="/become">发布我的服务 ${icon('arrow-right')}</a>
    </div>`;
  }
  return `<div class="manage-list">${guides.map(serviceItem).join('')}</div>`;
}

function accountShell(user) {
  return `
    <section class="account-hero ${user.coverUrl ? 'has-cover' : ''}" ${user.coverUrl ? `style="--account-cover:url('${escapeHTML(user.coverUrl)}')"` : ''}>
      <div class="account-orb" aria-hidden="true"></div>
      <div class="container">
        <nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><span>我的青禾</span></nav>
        <div class="account-hero-row">
          <div class="account-profile">
            ${avatar(user.name, user.avatarTone, 'xl', user.avatarUrl)}
            <div>
              <span class="eyebrow">MY QINGHE</span>
              <h1>${greeting()}，${escapeHTML(user.name)}</h1>
              <p>${escapeHTML(user.email)} <span class="dot-sep"></span> ${joinedDate(user.joinedAt)}${user.city ? ` <span class="dot-sep"></span> ${escapeHTML(user.city)}` : ''}</p>
              ${user.bio ? `<span class="account-bio">${escapeHTML(user.bio)}</span>` : ''}
              <a class="account-edit-link" href="/profile">${icon('edit')} 编辑个人资料</a>
            </div>
          </div>
          <div class="account-stats">
            <div><strong data-stat="active">—</strong><span>进行中的预约</span></div>
            <div><strong data-stat="completed">—</strong><span>已经完成的见面</span></div>
            <div><strong data-stat="services">—</strong><span>我的地陪服务</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="account-body">
      <div class="container account-layout">
        <aside class="account-side">
          <div class="account-side-card">
            <div class="account-side-head">
              ${avatar(user.name, user.avatarTone, 'md', user.avatarUrl)}
              <div><strong>${escapeHTML(user.name)}</strong><span>${escapeHTML(user.city || '城市待填写')}</span></div>
            </div>
            <nav class="account-nav" aria-label="个人中心导航">
              <button type="button" class="account-nav-item is-active" data-tab="bookings">${icon('calendar')} 我的预约 <span data-count="bookings">0</span></button>
              <button type="button" class="account-nav-item" data-tab="services">${icon('route')} 我的服务 <span data-count="services">0</span></button>
              <a class="account-nav-item account-nav-item--muted" href="/profile">${icon('user')} 个人资料 ${icon('arrow-up-right', 'nav-arrow')}</a>
            </nav>
            <div class="account-side-divider"></div>
            <button type="button" class="account-nav-item account-nav-item--muted" data-account-logout>${icon('logout')} 退出登录</button>
          </div>
          <div class="account-help-card">
            <span>${icon('shield')}</span>
            <div><strong>需要帮助？</strong><p>关于预约、取消或安全边界，可以随时联系青禾小助手。</p><button type="button" data-help>查看帮助</button></div>
          </div>
        </aside>
        <div class="account-main">
          <div class="account-main-head">
            <div>
              <span class="eyebrow" data-panel-eyebrow>MY BOOKINGS</span>
              <h2 data-panel-title>我的预约</h2>
              <p data-panel-sub>每一次出发，都值得被好好记住。</p>
            </div>
            <a class="btn btn--primary btn--sm" href="/guides">${icon('plus')} 新预约</a>
          </div>
          <div data-account-panels>
            <div class="skeleton-stack"><div class="skeleton skeleton-line"></div><div class="skeleton skeleton-block"></div><div class="skeleton skeleton-block"></div></div>
          </div>
        </div>
      </div>
    </section>`;
}

export async function renderAccount(root, route) {
  setPageTitle('我的青禾');
  if (!session.user) {
    root.innerHTML = gateShell();
    root.querySelector('[data-account-login]')?.addEventListener('click', async () => {
      const user = await openAuthModal({ mode: 'login', reason: '登录后即可查看你的预约和服务。' });
      if (user) renderAccount(root, route);
    });
    return;
  }

  const user = session.user;
  const initialTab = route.search.get('tab') === 'services' ? 'services' : 'bookings';
  root.innerHTML = accountShell(user);

  let bookings = [];
  let guides = [];
  let activeTab = initialTab;
  const panels = root.querySelector('[data-account-panels]');

  const updateStats = () => {
    const active = bookings.filter((b) => ['pending', 'confirmed'].includes(b.status)).length;
    const completed = bookings.filter((b) => b.status === 'completed').length;
    root.querySelector('[data-stat="active"]').textContent = String(active);
    root.querySelector('[data-stat="completed"]').textContent = String(completed);
    root.querySelector('[data-stat="services"]').textContent = String(guides.length);
    root.querySelector('[data-count="bookings"]').textContent = String(bookings.length);
    root.querySelector('[data-count="services"]').textContent = String(guides.length);
  };

  const setHeader = (tab) => {
    const isBookings = tab === 'bookings';
    root.querySelector('[data-panel-eyebrow]').textContent = isBookings ? 'MY BOOKINGS' : 'MY SERVICES';
    root.querySelector('[data-panel-title]').textContent = isBookings ? '我的预约' : '我的服务';
    root.querySelector('[data-panel-sub]').textContent = isBookings
      ? '每一次出发，都值得被好好记住。'
      : '管理你的地陪服务，决定什么时候接单。';
    root.querySelectorAll('[data-tab]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.tab === tab);
    });
  };

  const bindPanelActions = () => {
    panels.querySelectorAll('[data-cancel]').forEach((button) => {
      button.addEventListener('click', async () => {
        const booking = bookings.find((b) => b.id === button.dataset.cancel);
        if (!booking) return;
        const confirmed = await confirmDialog({
          title: '取消这笔预约？',
          message: `与 ${booking.guideName} 的 ${formatDateCN(booking.date)} 行程将被取消，确认前不会产生费用。`,
          confirmText: '确认取消',
          cancelText: '保留预约',
          danger: true
        });
        if (!confirmed) return;
        button.disabled = true;
        try {
          const result = await api(`/api/bookings/${encodeURIComponent(booking.id)}/cancel`, { method: 'PATCH' });
          Object.assign(booking, result.booking);
          toast('预约已取消，期待下一次出发', 'info');
          updateStats();
          renderPanel();
        } catch (error) {
          toast(error instanceof ApiError ? error.message : '取消失败，请稍后再试', 'error');
          button.disabled = false;
        }
      });
    });

    panels.querySelectorAll('[data-toggle-service]').forEach((button) => {
      button.addEventListener('click', async () => {
        const guide = guides.find((g) => g.id === button.dataset.toggleService);
        if (!guide) return;
        const nextStatus = guide.status === 'published' ? 'paused' : 'published';
        button.disabled = true;
        try {
          const result = await api(`/api/guides/${encodeURIComponent(guide.id)}`, {
            method: 'PATCH',
            body: { status: nextStatus }
          });
          Object.assign(guide, result.guide);
          toast(nextStatus === 'published' ? '服务已恢复接单' : '服务已暂停，旅人暂时看不到它', 'info');
          updateStats();
          renderPanel();
        } catch (error) {
          toast(error instanceof ApiError ? error.message : '操作失败，请稍后再试', 'error');
          button.disabled = false;
        }
      });
    });
  };

  const renderPanel = () => {
    setHeader(activeTab);
    panels.innerHTML = activeTab === 'bookings' ? bookingsPanel(bookings) : servicesPanel(guides);
    bindPanelActions();
    initReveals(panels);
  };

  const setTab = (tab, { updateUrl = true } = {}) => {
    activeTab = tab;
    if (updateUrl) replaceUrl(tab === 'services' ? '/account?tab=services' : '/account');
    renderPanel();
  };

  root.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => setTab(button.dataset.tab));
  });

  root.querySelector('[data-help]')?.addEventListener('click', () => {
    toast('帮助中心正在整理中，可先阅读社区公约与预约说明。', 'info');
  });
  root.querySelector('[data-account-logout]')?.addEventListener('click', async () => {
    await signOut();
    toast('已退出登录，随时欢迎回来', 'info');
    navigate('/');
  });

  try {
    const [bookingResult, guideResult] = await Promise.all([api('/api/bookings/mine'), api('/api/guides/mine')]);
    bookings = bookingResult.bookings;
    guides = guideResult.guides;
    updateStats();
    setTab(initialTab, { updateUrl: false });
  } catch (error) {
    panels.innerHTML = `<div class="inline-error">${icon('alert')} 暂时没能加载你的数据，<button type="button" class="text-link" data-retry>重新加载</button></div>`;
    panels.querySelector('[data-retry]')?.addEventListener('click', () => renderAccount(root, route));
  }
}
