import { api, ApiError } from './api.js?v=1.7.0';
import { requireAuth } from './components/auth-modal.js?v=1.7.0';
import { renderFooter, renderHeader } from './components/header.js?v=1.7.0';
import { renderAccount } from './pages/account.js?v=1.7.0';
import { renderBecome } from './pages/become.js?v=1.8.0';
import { renderGuideDetail } from './pages/detail.js?v=1.8.0';
import { renderGuides } from './pages/guides.js?v=1.7.0';
import { renderHome } from './pages/home.js?v=1.7.0';
import { renderProfile } from './pages/profile.js?v=1.7.0';
import { renderMessages } from './pages/messages.js?v=1.7.0';
import { renderMatching } from './pages/matching.js?v=1.7.0';
import { navigate, parseRoute, startRouter } from './router.js?v=1.7.0';
import { bootSession } from './session.js?v=1.7.0';
import { appState } from './state.js?v=1.7.0';
import {
  closeModal,
  icon,
  isModalOpen,
  setPageTitle,
  showComingSoon,
  showModal,
  toast,
  toggleFavorite
} from './ui.js?v=1.7.0';

function notFoundPage() {
  return `
    <section class="not-found container">
      <span class="not-found-mark">${icon('compass')}</span>
      <span class="eyebrow">LOST IN THE CITY</span>
      <h1>这条小路，好像走岔了</h1>
      <p>页面不存在，或者已经被收进了城市的某个抽屉。</p>
      <div class="not-found-actions">
        <a class="btn btn--primary" href="/">回到首页 ${icon('arrow-right')}</a>
        <a class="btn btn--ghost" href="/guides">去找地陪</a>
      </div>
    </section>`;
}

function renderRoute() {
  closeModal(true);
  renderHeader();
  const root = document.getElementById('app');
  if (!root) return;
  const route = parseRoute();
  document.body.dataset.page = route.name;
  root.className = 'site-main';
  root.innerHTML = '';

  try {
    switch (route.name) {
      case 'home':
        renderHome(root);
        break;
      case 'guides':
        renderGuides(root, route);
        break;
      case 'guide':
        renderGuideDetail(root, route);
        break;
      case 'become':
        renderBecome(root);
        break;
      case 'account':
        renderAccount(root, route);
        break;
      case 'profile':
        renderProfile(root, route);
        break;
      case 'messages':
        renderMessages(root, route);
        break;
      case 'matching':
        renderMatching(root);
        break;
      default:
        setPageTitle('页面走丢了');
        root.innerHTML = notFoundPage();
    }
  } catch (error) {
    console.error(error);
    setPageTitle('出了一点小状况');
    root.innerHTML = `<section class="not-found container"><span class="not-found-mark">${icon('alert')}</span><h1>页面暂时没能打开</h1><p>请刷新后再试，或者回到首页重新出发。</p><div class="not-found-actions"><a class="btn btn--primary" href="/">回到首页</a></div></section>`;
  }

  requestAnimationFrame(() => {
    root.classList.add('is-ready');
  });
}

function safetyModal() {
  showModal(
    `<div class="rules-modal">
      <span class="eyebrow">COMMUNITY & SAFETY</span>
      <h2>让每一次见面，都有边界和底气</h2>
      <p class="rules-lead">青禾希望把「找个人一起逛城市」这件简单的事，做得安全、透明、有分寸。</p>
      <div class="rules-grid">
        <article><span>${icon('pin')}</span><h3>公开场所见面</h3><p>第一次见面请选择咖啡馆、地铁站、热门地标等公开区域，不进入私密空间。</p></article>
        <article><span>${icon('message')}</span><h3>平台内先沟通</h3><p>行程、价格和边界都先聊清楚。不要私下转账，也不要接受让你不适的邀约。</p></article>
        <article><span>${icon('shield')}</span><h3>保留行程记录</h3><p>把预约和沟通留在平台内。遇到问题可以取消并反馈，我们会协助处理。</p></article>
        <article><span>${icon('leaf')}</span><h3>尊重彼此</h3><p>地陪是旅行陪伴服务，不是任何形式的越界陪伴。请尊重对方的时间、身体和意愿。</p></article>
      </div>
      <button type="button" class="btn btn--primary" data-modal-close>我明白了</button>
    </div>`,
    { className: 'modal--rules' }
  );
}

function creditsModal() {
  showModal(
    `<div class="rules-modal">
      <span class="eyebrow">IMAGE CREDITS</span>
      <h2>把好看的风景，认真署名</h2>
      <p class="rules-lead">页面中的城市与旅行照片来自 Unsplash 和 Wikimedia Commons。感谢每一位把世界拍下来的人。</p>
      <div class="credits-list">
        <div class="credit-group">
          <h3>Unsplash</h3>
          <p>上海城市照片、咖啡馆、相机、山野与茶饮图片，依据 <a href="https://unsplash.com/license" target="_blank" rel="noopener">Unsplash License</a> 使用。图片来源：
            <a href="https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2" target="_blank" rel="noopener">hero</a> ·
            <a href="https://images.unsplash.com/photo-1545893835-abaa50cbe628" target="_blank" rel="noopener">上海</a> ·
            <a href="https://images.unsplash.com/photo-1508804185872-d7badad00f7d" target="_blank" rel="noopener">长城</a> ·
            <a href="https://images.unsplash.com/photo-1564349683136-77e08dba1ef7" target="_blank" rel="noopener">熊猫</a> ·
            <a href="https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb" target="_blank" rel="noopener">咖啡馆</a> ·
            <a href="https://images.unsplash.com/photo-1516035069371-29a1b244cc32" target="_blank" rel="noopener">相机</a> ·
            <a href="https://images.unsplash.com/photo-1526772662000-3f88f10405ff" target="_blank" rel="noopener">山野</a> ·
            <a href="https://images.unsplash.com/photo-1544787219-7f47ccb76574" target="_blank" rel="noopener">茶</a>
          </p>
        </div>
        <div class="credit-group">
          <h3>Wikimedia Commons</h3>
          <p><strong>西安城墙</strong> · 摄影 xiquinhosilva · <a href="https://creativecommons.org/licenses/by/2.0" target="_blank" rel="noopener">CC BY 2.0</a></p>
          <p><strong>杭州西湖</strong> · 摄影 Peter Dowley · <a href="https://creativecommons.org/licenses/by/2.0" target="_blank" rel="noopener">CC BY 2.0</a></p>
          <p><strong>广州塔</strong> · 摄影 Daniel Lu · <a href="https://creativecommons.org/licenses/by-sa/4.0" target="_blank" rel="noopener">CC BY-SA 4.0</a></p>
        </div>
        <div class="credit-group">
          <h3>字体与图标</h3>
          <p>字体使用系统字体；图标与「青禾」品牌图形为项目内手写 SVG，不依赖第三方图标库。</p>
        </div>
      </div>
      <button type="button" class="btn btn--primary" data-modal-close>谢谢这些风景</button>
    </div>`,
    { className: 'modal--rules' }
  );
}

function bindGlobalActions() {
  document.addEventListener('click', async (event) => {
    const chatButton = event.target.closest('[data-chat-guide]');
    if (chatButton) {
      event.preventDefault();
      if (chatButton.disabled) return;
      chatButton.disabled = true;
      try {
        const user = await requireAuth('登录后就可以和这位地陪私聊啦。');
        if (!user) return;
        const { conversation } = await api('/api/conversations', {
          method: 'POST',
          body: { guideId: chatButton.dataset.chatGuide }
        });
        navigate(`/messages?conversation=${encodeURIComponent(conversation.id)}`);
      } catch (error) {
        toast(error instanceof ApiError ? error.message : '私聊暂时没有打开，请稍后再试', 'error');
      } finally {
        chatButton.disabled = false;
      }
      return;
    }

    const favorite = event.target.closest('[data-favorite]');
    if (favorite) {
      event.preventDefault();
      const id = favorite.dataset.favorite;
      const saved = toggleFavorite(id);
      document.querySelectorAll('[data-favorite]').forEach((button) => {
        if (button.dataset.favorite !== id) return;
        button.classList.toggle('is-saved', saved);
        button.setAttribute('aria-pressed', String(saved));
        button.setAttribute('aria-label', saved ? '取消收藏' : '收藏这位地陪');
      });
      toast(saved ? '已收藏这位地陪' : '已取消收藏', saved ? 'success' : 'info');
      return;
    }

    const coming = event.target.closest('[data-coming-soon]');
    if (coming) {
      event.preventDefault();
      showComingSoon({ name: coming.dataset.comingSoon });
      return;
    }

    if (event.target.closest('[data-safety]')) {
      event.preventDefault();
      safetyModal();
      return;
    }

    if (event.target.closest('[data-credits]')) {
      event.preventDefault();
      creditsModal();
    }
  });

  document.addEventListener(
    'click',
    (event) => {
      if (!isModalOpen()) return;
      if (event.target.closest('a[href]')) closeModal();
    },
    true
  );

  window.addEventListener('session:change', () => {
    renderHeader();
    setTimeout(() => {
      if (isModalOpen()) return;
      const route = parseRoute();
      if (route.name === 'account' && !document.querySelector('[data-account-panels]')) renderRoute();
      if (route.name === 'become' && !document.querySelector('[data-become-form]')) renderRoute();
      if (route.name === 'profile' && !document.querySelector('.profile-container')) renderRoute();
      if (route.name === 'messages' && !document.querySelector('[data-messages-shell]')) renderRoute();
      if (route.name === 'matching') renderRoute();
    }, 360);
  });

  window.addEventListener('popstate', () => renderHeader());
}

async function boot() {
  const root = document.getElementById('app');
  try {
    const [meta] = await Promise.all([api('/api/meta'), bootSession()]);
    appState.meta = meta;
    renderFooter();
    bindGlobalActions();
    startRouter(renderRoute);
    renderRoute();
    window.addEventListener('route:change', () => renderHeader());
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && document.body.classList.contains('drawer-open')) {
        document.querySelector('[data-mobile-toggle]')?.click();
      }
    });
  } catch (error) {
    console.error(error);
    if (root) {
      root.innerHTML = `
        <section class="not-found container">
          <span class="not-found-mark">${icon('leaf')}</span>
          <span class="eyebrow">A SMALL PAUSE</span>
          <h1>青禾正在慢慢醒来</h1>
          <p>没能连上本地服务。请确认服务已启动，再刷新页面试试。</p>
          <div class="not-found-actions">
            <button class="btn btn--primary" type="button" data-reload>重新加载</button>
            <a class="btn btn--ghost" href="/api/health" data-native="true">检查服务状态</a>
          </div>
        </section>`;
      root.querySelector('[data-reload]')?.addEventListener('click', () => window.location.reload());
    }
  }
}

boot();
