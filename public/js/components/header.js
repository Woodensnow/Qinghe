import { navigate } from '../router.js?v=1.7.0';
import { session, signOut } from '../session.js?v=1.7.0';
import { BRAND_MARK, avatar, escapeHTML, icon, toast } from '../ui.js?v=1.7.0';
import { openAuthModal } from './auth-modal.js?v=1.7.0';

let headerController = null;

function navLinks(current, mobile = false) {
  const links = [
    { href: '/', label: '首页', match: (path) => path === '/' },
    { href: '/guides', label: '找地陪', match: (path) => path.startsWith('/guides') },
    { href: '/matching', label: '双边匹配', match: (path) => path === '/matching' },
    { href: '/become', label: '成为地陪', match: (path) => path.startsWith('/become') }
  ];
  return links
    .map(
      (link) => `<a class="nav-link ${link.match(current) ? 'is-active' : ''} ${mobile ? 'nav-link--mobile' : ''}" href="${link.href}">
        <span>${link.label}</span>${mobile ? icon('arrow-up-right') : ''}
      </a>`
    )
    .join('');
}

function userMenu(user) {
  return `
    <div class="user-menu" data-user-menu>
      <button type="button" class="user-trigger" data-user-trigger aria-haspopup="menu" aria-expanded="false">
        ${avatar(user.name, user.avatarTone, 'sm', user.avatarUrl)}
        <span class="user-trigger-name">${escapeHTML(user.name)}</span>
        ${icon('chevron-down', 'user-trigger-chevron')}
      </button>
      <div class="user-dropdown" role="menu" data-user-dropdown>
        <div class="user-dropdown-head">
          <strong>${escapeHTML(user.name)}</strong>
          <span>${escapeHTML(user.email)}</span>
        </div>
        <a href="/messages" role="menuitem">${icon('message')} 消息</a>
        <a href="/profile" role="menuitem">${icon('user')} 个人资料</a>
        <a href="/account" role="menuitem">${icon('calendar')} 我的预约</a>
        <a href="/account?tab=services" role="menuitem">${icon('route')} 我的服务</a>
        <a href="/become" role="menuitem">${icon('plus')} 发布新服务</a>
        <div class="user-dropdown-divider"></div>
        <button type="button" role="menuitem" data-logout>${icon('logout')} 退出登录</button>
      </div>
    </div>`;
}

export function renderHeader() {
  const header = document.getElementById('site-header');
  if (!header) return;
  headerController?.abort();
  headerController = new AbortController();
  const { signal } = headerController;
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  const user = session.user;

  header.innerHTML = `
    <div class="header-inner container">
      <a class="brand" href="/" aria-label="青禾首页">
        ${BRAND_MARK}
        <span class="brand-type">
          <strong>青禾</strong>
          <small>QINGHE</small>
        </span>
      </a>
      <nav class="desktop-nav" aria-label="主导航">
        ${navLinks(path)}
        ${user ? `<a class="nav-link ${path.startsWith('/messages') ? 'is-active' : ''}" href="/messages">消息</a>` : ''}
      </nav>
      <div class="header-actions">
        <span class="header-divider" aria-hidden="true"></span>
        ${
          user
            ? `${userMenu(user)}`
            : `<button type="button" class="nav-login" data-login>登录</button>
               <a href="/become" class="btn btn--primary btn--sm header-cta">发布服务 ${icon('arrow-up-right')}</a>`
        }
        <button type="button" class="mobile-toggle" data-mobile-toggle aria-label="打开菜单" aria-expanded="false">
          <span></span><span></span><span></span>
        </button>
      </div>
    </div>
    <div class="mobile-drawer" data-mobile-drawer>
      <div class="mobile-drawer-inner">
        <nav class="mobile-nav" aria-label="移动端导航">
          ${navLinks(path, true)}
          ${user ? `<a class="nav-link nav-link--mobile ${path.startsWith('/messages') ? 'is-active' : ''}" href="/messages"><span>消息</span>${icon('arrow-up-right')}</a>` : ''}
        </nav>
        <div class="mobile-drawer-extra">
          ${
            user
              ? `<a class="mobile-user" href="/account">
                   ${avatar(user.name, user.avatarTone, 'md', user.avatarUrl)}
                   <span><strong>${escapeHTML(user.name)}</strong><small>查看我的预约</small></span>
                   ${icon('arrow-right')}
                 </a>
                 <button type="button" class="btn btn--soft btn--full" data-logout>${icon('logout')} 退出登录</button>`
              : `<button type="button" class="btn btn--primary btn--full" data-login>登录 / 注册 ${icon('arrow-right')}</button>`
          }
          <p class="mobile-drawer-note">${icon('leaf')} 把闲暇，变成一段好旅程</p>
        </div>
      </div>
    </div>`;

  const setScrolled = () => header.classList.toggle('is-scrolled', window.scrollY > 14);
  setScrolled();
  window.addEventListener('scroll', setScrolled, { passive: true, signal });

  const drawer = header.querySelector('[data-mobile-drawer]');
  const mobileToggle = header.querySelector('[data-mobile-toggle]');
  const closeDrawer = () => {
    drawer.classList.remove('is-open');
    mobileToggle.classList.remove('is-open');
    mobileToggle.setAttribute('aria-expanded', 'false');
    mobileToggle.setAttribute('aria-label', '打开菜单');
    document.body.classList.remove('drawer-open');
  };
  mobileToggle.addEventListener('click', () => {
    const open = !drawer.classList.contains('is-open');
    drawer.classList.toggle('is-open', open);
    mobileToggle.classList.toggle('is-open', open);
    mobileToggle.setAttribute('aria-expanded', String(open));
    mobileToggle.setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
    document.body.classList.toggle('drawer-open', open);
  });
  drawer.addEventListener('click', (event) => {
    if (event.target.closest('a') || event.target === drawer) closeDrawer();
  });
  window.addEventListener('route:change', closeDrawer, { signal });

  header.querySelectorAll('[data-login]').forEach((button) => {
    button.addEventListener('click', async () => {
      closeDrawer();
      await openAuthModal({ mode: 'login', reason: '登录后即可预约地陪、发布服务。' });
    });
  });

  const userTrigger = header.querySelector('[data-user-trigger]');
  if (userTrigger) {
    const menu = header.querySelector('[data-user-menu]');
    const setOpen = (open) => {
      menu.classList.toggle('is-open', open);
      userTrigger.setAttribute('aria-expanded', String(open));
    };
    userTrigger.addEventListener('click', (event) => {
      event.stopPropagation();
      setOpen(!menu.classList.contains('is-open'));
    });
    document.addEventListener(
      'click',
      (event) => {
        if (!menu.contains(event.target)) setOpen(false);
      },
      { signal }
    );
    document.addEventListener(
      'keydown',
      (event) => {
        if (event.key === 'Escape') setOpen(false);
      },
      { signal }
    );
  }

  header.querySelectorAll('[data-logout]').forEach((button) => {
    button.addEventListener('click', async () => {
      await signOut();
      closeDrawer();
      toast('已退出登录，随时欢迎回来', 'info');
      navigate('/');
    });
  });
}

export function renderFooter() {
  const footer = document.getElementById('site-footer');
  if (!footer) return;
  const year = new Date().getFullYear();
  footer.innerHTML = `
    <div class="container footer-main">
      <div class="footer-brand">
        <a class="brand brand--footer" href="/">
          ${BRAND_MARK}
          <span class="brand-type"><strong>青禾</strong><small>QINGHE</small></span>
        </a>
        <p>城市轻兼职，让每个人的闲暇时间<br>都能长出一段新的可能。</p>
        <div class="footer-badge">${icon('shield')} 真实认证 · 平台保障</div>
      </div>
      <div class="footer-col">
        <h3>发现</h3>
        <a href="/guides">找地陪</a>
        <a href="/guides?city=上海">上海地陪</a>
        <a href="/guides?city=北京">北京地陪</a>
        <button type="button" data-coming-soon="摄影">摄影 <span>即将开放</span></button>
        <button type="button" data-coming-soon="模特">模特 <span>即将开放</span></button>
      </div>
      <div class="footer-col">
        <h3>加入青禾</h3>
        <a href="/become">成为地陪</a>
        <a href="/account">我的预约</a>
        <a href="/profile">个人资料</a>
        <a href="/messages">消息</a>
        <button type="button" data-coming-soon="博物馆讲解员">博物馆讲解员 <span>即将开放</span></button>
        <button type="button" data-coming-soon="NPC">NPC <span>即将开放</span></button>
      </div>
      <div class="footer-col">
        <h3>关于</h3>
        <button type="button" data-safety>社区公约</button>
        <button type="button" data-safety>服务保障</button>
        <button type="button" data-safety>隐私说明</button>
        <button type="button" data-credits>图片致谢</button>
        <a href="mailto:hello@qinghe.demo">联系我们</a>
      </div>
    </div>
    <div class="container footer-bottom">
      <p>© ${year} 青禾 QINGHE · 城市轻兼职</p>
      <p class="footer-note">${icon('leaf')} 演示项目 · 资料、预约与照片仅保存在本机</p>
    </div>`;
}
