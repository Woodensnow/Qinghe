import { api, ApiError } from '../api.js?v=1.7.0';
import { applySession, session } from '../session.js?v=1.7.0';
import { BRAND_MARK, closeModal, escapeHTML, icon, showModal, toast } from '../ui.js?v=1.7.0';

function field({ name, label, type = 'text', placeholder = '', iconName = '', autocomplete = '', value = '', hint = '' }) {
  return `
    <label class="field">
      <span class="field-label">${label}</span>
      <span class="input-wrap">
        ${iconName ? `<span class="input-icon">${icon(iconName)}</span>` : ''}
        <input class="${iconName ? 'has-icon' : ''}" type="${type}" name="${name}" placeholder="${escapeHTML(placeholder)}"
          value="${escapeHTML(value)}" autocomplete="${autocomplete}" ${type === 'password' ? 'minlength="6"' : ''}>
        ${type === 'password' ? `<button class="input-action" type="button" data-toggle-password aria-label="显示密码">${icon('eye')}</button>` : ''}
      </span>
      ${hint ? `<span class="field-hint">${hint}</span>` : ''}
      <span class="field-error" data-error-for="${name}"></span>
    </label>`;
}

function loginForm(email = '') {
  return `
    <form class="auth-form" data-auth-form novalidate>
      ${field({ name: 'email', label: '邮箱', type: 'email', placeholder: 'you@example.com', iconName: 'mail', autocomplete: 'email', value: email })}
      ${field({ name: 'password', label: '密码', type: 'password', placeholder: '输入你的密码', iconName: 'lock', autocomplete: 'current-password' })}
      <div class="auth-form-meta">
        <label class="checkline"><input type="checkbox" name="remember" checked><span>记住我</span></label>
        <button type="button" class="text-link" data-forgot>忘记密码？</button>
      </div>
      <p class="auth-error" data-auth-error role="alert"></p>
      <button class="btn btn--primary btn--full btn--lg" type="submit" data-submit>
        <span>登录</span>${icon('arrow-right')}
      </button>
      <p class="auth-switch">还没有账号？<button type="button" class="text-link" data-switch="register">免费注册</button></p>
    </form>`;
}

function registerForm(email = '') {
  return `
    <form class="auth-form" data-auth-form novalidate>
      ${field({ name: 'name', label: '怎么称呼你', type: 'text', placeholder: '例如：小禾', iconName: 'user', autocomplete: 'nickname' })}
      ${field({ name: 'email', label: '邮箱', type: 'email', placeholder: 'you@example.com', iconName: 'mail', autocomplete: 'email', value: email })}
      ${field({ name: 'password', label: '设置密码', type: 'password', placeholder: '至少 6 位字符', iconName: 'lock', autocomplete: 'new-password', hint: '密码仅以加密形式保存在本机演示数据中' })}
      <label class="checkline auth-agree">
        <input type="checkbox" name="agree">
        <span>我已阅读并同意 <button type="button" class="text-link" data-rules>社区公约</button>，愿意以真诚和尊重对待每一次相遇。</span>
      </label>
      <span class="field-error" data-error-for="agree"></span>
      <p class="auth-error" data-auth-error role="alert"></p>
      <button class="btn btn--primary btn--full btn--lg" type="submit" data-submit>
        <span>创建账号</span>${icon('arrow-right')}
      </button>
      <p class="auth-switch">已经有账号了？<button type="button" class="text-link" data-switch="login">直接登录</button></p>
    </form>`;
}

export function openAuthModal({ mode = 'login', reason = '' } = {}) {
  if (session.user) return Promise.resolve(session.user);

  return new Promise((resolve) => {
    let currentMode = mode;
    let settled = false;
    let rememberedEmail = '';

    const finish = (user) => {
      if (settled) return;
      settled = true;
      resolve(user || null);
    };

    const shell = () => `
      <div class="auth-modal">
        <aside class="auth-aside">
          <div class="auth-aside-image" aria-hidden="true"></div>
          <div class="auth-aside-content">
            <span class="auth-brand">${BRAND_MARK}<span>青禾</span></span>
            <div class="auth-aside-quote">
              <span class="eyebrow eyebrow--light">A LITTLE TIME, A NEW CITY</span>
              <h2>把空闲时间，<br>变成一段好旅程。</h2>
              <p>找一位懂城市的人，或成为那个带别人认识城市的人。</p>
            </div>
            <div class="auth-aside-tags">
              <span>${icon('shield')} 真实身份认证</span>
              <span>${icon('leaf')} 无购物纯玩</span>
            </div>
          </div>
        </aside>
        <section class="auth-content">
          <span class="auth-kicker" data-auth-kicker>WELCOME BACK</span>
          <h2 data-auth-title>欢迎回到青禾</h2>
          <p class="auth-sub" data-auth-sub>登录后，收藏路线、预约地陪，也可以发布自己的服务。</p>
          ${reason ? `<p class="auth-reason">${icon('info')} ${escapeHTML(reason)}</p>` : ''}
          <div class="auth-tabs" role="tablist" aria-label="登录或注册">
            <button type="button" role="tab" data-tab="login" aria-selected="true">登录</button>
            <button type="button" role="tab" data-tab="register" aria-selected="false">注册</button>
            <span class="auth-tab-indicator"></span>
          </div>
          <div data-auth-form-wrap></div>
          <div class="auth-demo">
            <div>
              <strong>第一次来青禾？</strong>
              <span>用体验账号直接逛逛</span>
            </div>
            <button type="button" class="btn btn--soft btn--sm" data-demo>${icon('sparkles')} 一键体验</button>
          </div>
        </section>
      </div>`;

    const modal = showModal(shell(), {
      className: 'modal--auth',
      showClose: true,
      closeOnBackdrop: false,
      onClose: () => finish(null)
    });

    const dialog = modal.dialog;
    const content = dialog.querySelector('[data-auth-form-wrap]');

    const setMode = (nextMode, email = '') => {
      currentMode = nextMode;
      rememberedEmail = email || rememberedEmail;
      dialog.querySelector('[data-auth-kicker]').textContent = nextMode === 'login' ? 'WELCOME BACK' : 'JOIN QINGHE';
      dialog.querySelector('[data-auth-title]').textContent = nextMode === 'login' ? '欢迎回到青禾' : '开始你的城市副业';
      dialog.querySelector('[data-auth-sub]').textContent =
        nextMode === 'login'
          ? '登录后，收藏路线、预约地陪，也可以发布自己的服务。'
          : '注册只需要一分钟。先看看，或者直接成为地陪。';
      dialog.querySelectorAll('[data-tab]').forEach((tab) => {
        tab.setAttribute('aria-selected', String(tab.dataset.tab === nextMode));
      });
      content.innerHTML = nextMode === 'login' ? loginForm(rememberedEmail) : registerForm(rememberedEmail);
      content.querySelector('input:not([type="checkbox"])')?.focus({ preventScroll: true });
      bindForm();
    };

    const setFieldError = (name, message) => {
      const holder = content.querySelector(`[data-error-for="${name}"]`);
      if (holder) holder.textContent = message || '';
      const input = content.querySelector(`[name="${name}"]`);
      if (input) input.classList.toggle('is-invalid', Boolean(message));
    };

    const clearErrors = () => {
      content.querySelectorAll('.field-error').forEach((el) => (el.textContent = ''));
      content.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
      const error = content.querySelector('[data-auth-error]');
      if (error) error.textContent = '';
    };

    const showError = (message, fieldName) => {
      const error = content.querySelector('[data-auth-error]');
      if (error) error.textContent = message;
      if (fieldName) setFieldError(fieldName, message);
    };

    const submit = async (event) => {
      event.preventDefault();
      clearErrors();
      const form = content.querySelector('[data-auth-form]');
      const values = Object.fromEntries(new FormData(form));
      const email = String(values.email || '').trim();
      const password = String(values.password || '');

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('请输入有效的邮箱地址', 'email');
        form.elements.email?.focus();
        return;
      }
      if (password.length < 6) {
        showError('密码至少需要 6 位字符', 'password');
        form.elements.password?.focus();
        return;
      }

      if (currentMode === 'register') {
        const name = String(values.name || '').trim();
        if (Array.from(name).length < 2) {
          showError('昵称至少需要 2 个字符', 'name');
          form.elements.name?.focus();
          return;
        }
        if (!values.agree) {
          showError('请先阅读并同意社区公约', 'agree');
          return;
        }
      }

      const submitButton = form.querySelector('[data-submit]');
      const original = submitButton.innerHTML;
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner"></span><span>请稍候…</span>';

      try {
        const endpoint = currentMode === 'login' ? '/api/auth/login' : '/api/auth/register';
        const payload = currentMode === 'login' ? { email, password } : { name: values.name, email, password };
        const result = await api(endpoint, { method: 'POST', body: payload });
        settled = true;
        applySession(result.token, result.user);
        toast(currentMode === 'login' ? `欢迎回来，${result.user.name}` : `欢迎加入青禾，${result.user.name}`);
        closeModal();
        resolve(result.user);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '登录失败，请稍后再试';
        showError(message, error.field);
        submitButton.disabled = false;
        submitButton.innerHTML = original;
      }
    };

    const bindForm = () => {
      const form = content.querySelector('[data-auth-form]');
      form.addEventListener('submit', submit);
      form.querySelectorAll('[data-toggle-password]').forEach((button) => {
        button.addEventListener('click', () => {
          const input = button.closest('.input-wrap').querySelector('input');
          const show = input.type === 'password';
          input.type = show ? 'text' : 'password';
          button.innerHTML = icon(show ? 'eye-off' : 'eye');
          button.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
        });
      });
      form.querySelector('[data-switch]')?.addEventListener('click', (event) => {
        const next = event.currentTarget.dataset.switch;
        setMode(next, form.elements.email?.value || rememberedEmail);
      });
      form.querySelector('[data-forgot]')?.addEventListener('click', () => {
        toast('演示版暂未接入邮件服务，请使用体验账号登录', 'info');
      });
      form.querySelector('[data-rules]')?.addEventListener('click', () => {
        toast('社区公约：真诚沟通、尊重边界、拒绝私下交易和任何不安全邀约。', 'info');
      });
      form.querySelectorAll('input').forEach((input) => {
        input.addEventListener('input', () => {
          if (input.closest('.field')) {
            const name = input.name;
            setFieldError(name, '');
          }
          const error = content.querySelector('[data-auth-error]');
          if (error) error.textContent = '';
        });
      });
    };

    dialog.querySelectorAll('[data-tab]').forEach((tab) => {
      tab.addEventListener('click', () => {
        if (tab.dataset.tab === currentMode) return;
        const email = content.querySelector('[name="email"]')?.value || rememberedEmail;
        setMode(tab.dataset.tab, email);
      });
    });

    dialog.querySelector('[data-demo]').addEventListener('click', () => {
      setMode('login');
      const form = content.querySelector('[data-auth-form]');
      form.elements.email.value = 'demo@qinghe.cn';
      form.elements.password.value = 'qinghe123';
      form.requestSubmit();
    });

    setMode(mode);
  });
}

export async function requireAuth(reason = '登录后就可以继续啦', options = {}) {
  if (session.user) return session.user;
  return openAuthModal({ reason, ...options });
}
