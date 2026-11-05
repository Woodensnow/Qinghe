import { api, ApiError } from '../api.js?v=1.7.0';
import { openAuthModal } from '../components/auth-modal.js?v=1.7.0';
import { replaceUrl } from '../router.js?v=1.7.0';
import { session } from '../session.js?v=1.7.0';
import { avatar, escapeHTML, icon, initReveals, setPageTitle, toast } from '../ui.js?v=1.7.0';

function messageTime(iso, withDate = false) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const time = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
  if (sameDay && !withDate) return time;
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${time}`;
}

function gateShell() {
  return `
    <section class="account-gate">
      <div class="account-gate-card">
        <div class="account-gate-visual">
          <span class="gate-mark">${icon('message')}</span>
          <span class="account-gate-line"></span>
          <span class="account-gate-route">${icon('leaf')}</span>
        </div>
        <div>
          <span class="eyebrow">PRIVATE CHAT</span>
          <h1>登录后，<br>和本地搭子聊一聊。</h1>
          <p>私聊只属于你和对方。出发前先聊聊路线、节奏和边界，让见面更安心。</p>
          <button type="button" class="btn btn--primary btn--lg" data-messages-login>登录 / 注册 ${icon('arrow-right')}</button>
          <div class="gate-benefits">
            <span>${icon('shield')} 仅双方可见</span>
            <span>${icon('message')} 行前沟通</span>
            <span>${icon('leaf')} 不私下交易</span>
          </div>
        </div>
      </div>
    </section>`;
}

function listSkeleton() {
  return `<div class="conversation-skeleton">
    <span class="skeleton skeleton-line skeleton-line--short"></span>
    <span class="skeleton skeleton-line"></span>
    <span class="skeleton skeleton-line skeleton-line--medium"></span>
  </div>`.repeat(3);
}

export function renderMessages(root, route) {
  setPageTitle('消息');
  if (!session.user) {
    root.innerHTML = gateShell();
    root.querySelector('[data-messages-login]')?.addEventListener('click', async () => {
      const user = await openAuthModal({ mode: 'login', reason: '登录后才能和地陪私聊。' });
      if (user) renderMessages(root, route);
    });
    return;
  }

  root.innerHTML = `
    <div class="container messages-container">
      <nav class="breadcrumb messages-breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><span>消息</span></nav>
      <div class="messages-shell" data-messages-shell>
        <aside class="conversations-panel">
          <div class="conversations-head">
            <div>
              <span class="eyebrow">PRIVATE CHAT</span>
              <h1>消息</h1>
            </div>
            <span class="conversations-count" data-conversation-count>—</span>
          </div>
          <p class="conversations-sub">行程开始前，先聊聊彼此期待。</p>
          <div class="conversations-list" data-conversation-list>${listSkeleton()}</div>
        </aside>
        <section class="thread-panel" data-thread-panel>
          <div class="thread-empty">
            <span class="empty-icon">${icon('message')}</span>
            <span class="eyebrow">YOUR CONVERSATIONS</span>
            <h2>选一段对话，<br>打个招呼吧。</h2>
            <p>从地陪卡片上的「私聊」开始，聊聊日期、路线，或者只是你此刻的心情。</p>
            <a class="btn btn--primary" href="/guides">去找地陪 ${icon('arrow-right')}</a>
          </div>
        </section>
      </div>
    </div>`;

  const shell = root.querySelector('[data-messages-shell]');
  const listEl = root.querySelector('[data-conversation-list]');
  const countEl = root.querySelector('[data-conversation-count]');
  const threadEl = root.querySelector('[data-thread-panel]');
  let conversations = [];
  let activeId = null;
  let activeConversation = null;
  let messages = [];
  let timer = null;
  let loadingThread = false;

  const stopTimer = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };
  window.addEventListener('route:change', stopTimer, { once: true });

  const unreadTotal = () => conversations.reduce((total, conversation) => total + (conversation.unread || 0), 0);

  const renderList = () => {
    countEl.textContent = unreadTotal() ? `${unreadTotal()} 条未读` : `${conversations.length} 段对话`;
    if (!conversations.length) {
      listEl.innerHTML = `<div class="conversations-empty">
        <span>${icon('edit')}</span>
        <strong>还没有私聊</strong>
        <p>在找地陪页看到感兴趣的人，点「私聊」就能开始。</p>
        <a class="btn btn--soft btn--sm" href="/guides">去看看地陪</a>
      </div>`;
      return;
    }
    listEl.innerHTML = conversations
      .map(
        (conversation) => `
        <button type="button" class="conversation-item ${conversation.id === activeId ? 'is-active' : ''}" data-conversation="${escapeHTML(conversation.id)}">
          <span class="conversation-avatar">${avatar(conversation.otherName, conversation.otherAvatarTone, 'md', conversation.otherAvatarUrl)}</span>
          <span class="conversation-copy">
            <span class="conversation-top">
              <strong>${escapeHTML(conversation.otherName)}</strong>
              <small>${messageTime(conversation.lastMessageAt)}</small>
            </span>
            <span class="conversation-context">${conversation.role === 'traveler' ? `${escapeHTML(conversation.guideName)} · ${escapeHTML(conversation.guideCity)}` : `旅人 · ${escapeHTML(conversation.guideCity)}`}</span>
            <span class="conversation-last">${escapeHTML(conversation.lastMessage || '开始聊聊吧…')}</span>
          </span>
          ${conversation.unread ? `<span class="conversation-unread">${conversation.unread}</span>` : ''}
        </button>`
      )
      .join('');
  };

  const renderThread = () => {
    if (!activeConversation) {
      shell.classList.remove('has-thread');
      threadEl.innerHTML = `<div class="thread-empty">
        <span class="empty-icon">${icon('message')}</span>
        <span class="eyebrow">YOUR CONVERSATIONS</span>
        <h2>选一段对话，<br>打个招呼吧。</h2>
        <p>从地陪卡片上的「私聊」开始，聊聊日期、路线，或者只是你此刻的心情。</p>
        <a class="btn btn--primary" href="/guides">去找地陪 ${icon('arrow-right')}</a>
      </div>`;
      return;
    }
    shell.classList.add('has-thread');
    const conversation = activeConversation;
    threadEl.innerHTML = `
      <header class="thread-head">
        <button type="button" class="thread-back" data-thread-back aria-label="返回对话列表">${icon('arrow-left')}</button>
        <span class="thread-avatar">${avatar(conversation.otherName, conversation.otherAvatarTone, 'md', conversation.otherAvatarUrl)}</span>
        <div class="thread-person">
          <strong>${escapeHTML(conversation.otherName)}</strong>
          <span>${escapeHTML(conversation.otherRoleLabel)} · ${escapeHTML(conversation.guideCity)}</span>
        </div>
        <a class="btn btn--ghost btn--sm thread-guide-link" href="/guides/${encodeURIComponent(conversation.guideId)}">查看地陪</a>
      </header>
      <div class="thread-messages" data-message-stream>
        ${
          messages.length
            ? messages
                .map((message) => {
                  const mine = message.senderRole === conversation.role;
                  return `<div class="message-row ${mine ? 'is-mine' : ''}">
                    ${mine ? '' : `<span class="message-avatar">${avatar(conversation.otherName, conversation.otherAvatarTone, 'sm', conversation.otherAvatarUrl)}</span>`}
                    <div class="message-bubble">
                      <p>${escapeHTML(message.body).replaceAll('\n', '<br>')}</p>
                      <span>${messageTime(message.createdAt, true)}</span>
                    </div>
                  </div>`;
                })
                .join('')
            : `<div class="thread-start">
                <span>${icon('leaf')}</span>
                <strong>从一句「你好」开始</strong>
                <p>可以先告诉对方你的出行日期、想去的路线，或者你喜欢怎样的节奏。</p>
              </div>`
        }
      </div>
      <form class="message-composer" data-message-form>
        <textarea name="body" rows="1" maxlength="1000" placeholder="写下你想说的话…" aria-label="消息内容"></textarea>
        <button class="btn btn--primary" type="submit" data-send-message>发送 ${icon('send')}</button>
      </form>`;
    bindThread();
    requestAnimationFrame(() => {
      const stream = threadEl.querySelector('[data-message-stream]');
      if (stream) stream.scrollTop = stream.scrollHeight;
    });
  };

  const bindThread = () => {
    threadEl.querySelector('[data-thread-back]')?.addEventListener('click', () => {
      activeId = null;
      activeConversation = null;
      messages = [];
      stopTimer();
      shell.classList.remove('has-thread');
      replaceUrl('/messages');
      renderList();
      renderThread();
    });

    const form = threadEl.querySelector('[data-message-form]');
    form?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const input = form.elements.body;
      const text = input.value.trim();
      if (!text || !activeId) return;
      const button = form.querySelector('[data-send-message]');
      button.disabled = true;
      try {
        const result = await api(`/api/conversations/${encodeURIComponent(activeId)}/messages`, {
          method: 'POST',
          body: { body: text }
        });
        messages.push(result.message);
        activeConversation = result.conversation;
        const index = conversations.findIndex((conversation) => conversation.id === activeId);
        if (index >= 0) {
          conversations[index] = { ...conversations[index], ...result.conversation };
        }
        input.value = '';
        input.style.height = '';
        renderThread();
        renderList();
      } catch (error) {
        toast(error instanceof ApiError ? error.message : '消息没有发出去，请稍后再试', 'error');
        button.disabled = false;
      }
    });

    const textarea = threadEl.querySelector('textarea[name="body"]');
    textarea?.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    });
    textarea?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
  };

  const startPolling = () => {
    stopTimer();
    timer = setInterval(async () => {
      if (!activeId || loadingThread) return;
      try {
        const result = await api(`/api/conversations/${encodeURIComponent(activeId)}/messages`);
        const last = messages[messages.length - 1];
        const incoming = result.messages[result.messages.length - 1];
        if (result.messages.length !== messages.length || incoming?.id !== last?.id) {
          const draft = threadEl.querySelector('textarea[name="body"]')?.value || '';
          const hadFocus = document.activeElement === threadEl.querySelector('textarea[name="body"]');
          messages = result.messages;
          activeConversation = result.conversation;
          renderThread();
          const nextInput = threadEl.querySelector('textarea[name="body"]');
          if (nextInput && draft) {
            nextInput.value = draft;
            nextInput.style.height = `${Math.min(nextInput.scrollHeight, 120)}px`;
            if (hadFocus) nextInput.focus();
          }
          const index = conversations.findIndex((conversation) => conversation.id === activeId);
          if (index >= 0) conversations[index] = { ...conversations[index], ...result.conversation, unread: 0 };
          renderList();
        }
      } catch {
        /* 静默轮询失败，不打扰阅读 */
      }
    }, 4000);
  };

  const selectConversation = async (id, { updateUrl = true } = {}) => {
    if (!id) return;
    activeId = id;
    loadingThread = true;
    stopTimer();
    shell.classList.add('has-thread');
    threadEl.innerHTML = `<div class="thread-loading"><span class="spinner"></span><span>正在打开对话…</span></div>`;
    renderList();
    if (updateUrl) replaceUrl(`/messages?conversation=${encodeURIComponent(id)}`);
    try {
      const result = await api(`/api/conversations/${encodeURIComponent(id)}/messages`);
      if (activeId !== id) return;
      messages = result.messages;
      activeConversation = result.conversation;
      const index = conversations.findIndex((conversation) => conversation.id === id);
      if (index >= 0) conversations[index] = { ...conversations[index], ...result.conversation, unread: 0 };
      renderThread();
      renderList();
      startPolling();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : '对话打开失败', 'error');
      activeId = null;
      activeConversation = null;
      shell.classList.remove('has-thread');
      renderList();
      renderThread();
    } finally {
      loadingThread = false;
    }
  };

  listEl.addEventListener('click', (event) => {
    const button = event.target.closest('[data-conversation]');
    if (!button) return;
    selectConversation(button.dataset.conversation);
  });

  api('/api/conversations')
    .then((result) => {
      conversations = result.conversations;
      renderList();
      const fromUrl = route.search.get('conversation');
      if (fromUrl && conversations.some((conversation) => conversation.id === fromUrl)) {
        selectConversation(fromUrl, { updateUrl: false });
      } else if (window.innerWidth > 960 && conversations.length) {
        selectConversation(conversations[0].id, { updateUrl: true });
      }
    })
    .catch((error) => {
      listEl.innerHTML = `<div class="conversations-empty"><span>${icon('alert')}</span><strong>消息暂时没有加载出来</strong><p>${escapeHTML(error instanceof ApiError ? error.message : '请刷新后再试')}</p></div>`;
    });

  initReveals(root);
}
