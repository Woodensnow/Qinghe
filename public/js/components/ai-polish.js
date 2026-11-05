import { api, ApiError } from '../api.js?v=1.7.0';
import { closeModal, escapeHTML, icon, showModal, toast } from '../ui.js?v=1.7.0';

export function openPolishModal({ text, scene, city = '', onApply }) {
  const source = String(text || '').trim();
  if (Array.from(source).length < 6) {
    toast('先写几句完整的话，AI 才有素材可以润色', 'info');
    return;
  }

  let variant = 0;
  let busy = false;

  const modal = showModal(
    `<div class="ai-polish-modal">
      <div class="ai-polish-head">
        <span class="ai-orb">${icon('sparkles')}</span>
        <div>
          <span class="eyebrow">AI TEXT POLISH</span>
          <h2>让表达更有温度</h2>
          <p>保留你的经历和语气，把句子调整得更自然、更有画面感。</p>
        </div>
      </div>
      <div class="ai-polish-body" data-ai-body></div>
    </div>`,
    { className: 'modal--ai' }
  );

  const body = modal.dialog.querySelector('[data-ai-body]');

  const renderLoading = () => {
    body.innerHTML = `<div class="ai-loading">
      <span class="ai-loading-orb">${icon('sparkles')}</span>
      <strong>正在理解你的表达${'…'}</strong>
      <p>保留事实，调整节奏和语气</p>
      <span class="ai-loading-dots"><i></i><i></i><i></i></span>
    </div>`;
  };

  const renderError = (message) => {
    body.innerHTML = `<div class="ai-error">
      <span>${icon('alert')}</span>
      <strong>这次没有润色成功</strong>
      <p>${escapeHTML(message)}</p>
      <button type="button" class="btn btn--primary btn--sm" data-ai-retry>再试一次</button>
    </div>`;
    body.querySelector('[data-ai-retry]')?.addEventListener('click', run);
  };

  const renderResult = (polished) => {
    body.innerHTML = `<div class="ai-result">
      <div class="ai-result-head">
        <span>润色后</span>
        <small>保留原意 · 表达更顺</small>
      </div>
      <div class="ai-result-text">${escapeHTML(polished).replaceAll('\n', '<br>')}</div>
      <details class="ai-original">
        <summary>看看润色前的原文</summary>
        <p>${escapeHTML(source).replaceAll('\n', '<br>')}</p>
      </details>
      <div class="ai-actions">
        <button type="button" class="btn btn--primary" data-ai-apply>替换原文 ${icon('check')}</button>
        <button type="button" class="btn btn--ghost" data-ai-retry>再润色一次 ${icon('sparkles')}</button>
      </div>
      <span class="ai-note">${icon('leaf')} 本地 AI 润色引擎 · 不会替你编造新的经历</span>
    </div>`;
    body.querySelector('[data-ai-apply]')?.addEventListener('click', () => {
      if (typeof onApply === 'function') onApply(polished);
      closeModal();
      toast('已替换为润色后的文字，可以继续修改');
    });
    body.querySelector('[data-ai-retry]')?.addEventListener('click', () => {
      variant += 1;
      run();
    });
  };

  const run = async () => {
    if (busy) return;
    busy = true;
    renderLoading();
    try {
      const result = await api('/api/ai/polish', {
        method: 'POST',
        body: { text: source, scene, city, variant }
      });
      renderResult(result.text);
    } catch (error) {
      renderError(error instanceof ApiError ? error.message : '请稍后再试');
    } finally {
      busy = false;
    }
  };

  run();
}
