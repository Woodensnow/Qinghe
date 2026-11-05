import { api, ApiError } from '../api.js?v=1.7.0';
import { openPolishModal } from '../components/ai-polish.js?v=1.7.0';
import { compressImageFile } from '../image.js?v=1.7.0';
import { openAuthModal } from '../components/auth-modal.js?v=1.7.0';
import { navigate } from '../router.js?v=1.7.0';
import { session, updateSessionUser } from '../session.js?v=1.7.0';
import { appState } from '../state.js?v=1.7.0';
import {
  avatar,
  cityOptionsHTML,
  escapeHTML,
  icon,
  initReveals,
  money,
  setPageTitle,
  toast
} from '../ui.js?v=1.7.0';

const SERVICE_META = {
  城市漫步: { icon: 'walk', note: '街巷、老建筑、城市故事' },
  美食探店: { icon: 'food', note: '本地小馆与市场里的味道' },
  接送陪同: { icon: 'car', note: '机场、车站与初到安顿' },
  拍照陪游: { icon: 'camera', note: '边走边拍，留下自然瞬间' },
  亲子出行: { icon: 'child', note: '节奏舒缓，适合带小朋友' },
  周边包车: { icon: 'route', note: '城市周边的一日小旅行' }
};

function formField({ name, label, placeholder, type = 'text', value = '', hint = '', maxlength = '', required = false, counter = false, tag = 'input' }) {
  const input =
    tag === 'textarea'
      ? `<textarea name="${name}" rows="5" ${maxlength ? `maxlength="${maxlength}"` : ''} placeholder="${escapeHTML(placeholder)}" ${required ? 'required' : ''}>${escapeHTML(value)}</textarea>`
      : `<input type="${type}" name="${name}" value="${escapeHTML(value)}" ${maxlength ? `maxlength="${maxlength}"` : ''} placeholder="${escapeHTML(placeholder)}" ${required ? 'required' : ''}>`;
  return `
    <label class="field">
      <span class="field-label">${label}${required ? '<em>*</em>' : ''}${counter ? `<small data-counter-for="${name}">0 / ${maxlength}</small>` : ''}</span>
      <span class="input-wrap input-wrap--plain">${input}</span>
      ${hint ? `<span class="field-hint">${hint}</span>` : ''}
      <span class="field-error" data-error-for="${name}"></span>
    </label>`;
}

function gateShell(user) {
  return `
    <div class="become-gate">
      <div class="become-gate-inner">
        <span class="gate-mark">${icon('lock')}</span>
        <span class="eyebrow">ONE MINUTE TO JOIN</span>
        <h2>登录后，开始发布你的服务</h2>
        <p>不需要押金，不需要面试。先认真介绍一下你和你的城市，我们会把真实的你展示给旅人。</p>
        <button type="button" class="btn btn--primary btn--lg" data-gate-login>登录 / 注册 ${icon('arrow-right')}</button>
        <div class="gate-benefits">
          <span>${icon('clock')} 时间自己定</span>
          <span>${icon('wallet')} 半日 ¥200 起</span>
          <span>${icon('shield')} 平台保障</span>
        </div>
      </div>
      <div class="become-gate-aside">
        <span class="eyebrow eyebrow--light">A DAY IN YOUR CITY</span>
        <blockquote>“原来我习以为常的日常，<br>是别人专程而来的风景。”</blockquote>
        <div class="gate-host">
          ${avatar('林小满', 'sage', 'md')}
          <div><strong>林小满</strong><span>上海 · 已陪伴 186 位旅人</span></div>
        </div>
        <span class="gate-stamp">${icon('leaf')} LOCAL<br>HOST</span>
      </div>
    </div>`;
}

function formShell(user, meta) {
  const covers = meta.coverPresets || [];
  const tones = meta.avatarTones || ['sage'];
  return `
    <form class="become-form" data-become-form novalidate>
      <div class="form-section">
        <div class="form-section-head">
          <span class="form-step">01</span>
          <div><h2>先介绍一下自己</h2><p>旅人最先看到的，是你的语气和你的城市。</p></div>
        </div>
        <div class="form-grid form-grid--two">
          ${formField({ name: 'name', label: '接单昵称', placeholder: '让大家怎么称呼你', value: user.name, maxlength: 12, required: true })}
          <label class="field">
            <span class="field-label">服务城市<em>*</em></span>
            <span class="input-wrap input-wrap--plain">
              <select name="city">${cityOptionsHTML(meta.cityGroups, user.city, { allLabel: '选择你生活的城市' })}</select>
            </span>
            <span class="field-error" data-error-for="city"></span>
          </label>
        </div>
        ${formField({ name: 'headline', label: '一句话介绍', placeholder: '例如：像本地朋友一样，带你钻进梧桐区的小马路', maxlength: 40, required: true, counter: true })}
        <label class="field">
          <span class="field-label">关于你 <em>*</em><small data-counter-for="bio">0 / 600</small></span>
          <span class="input-wrap input-wrap--plain">
            <textarea name="bio" rows="6" maxlength="600" placeholder="说说你在这座城市生活了多久、喜欢带朋友去哪里、你的节奏是什么样的。真诚比华丽更有用。"></textarea>
          </span>
          <div class="ai-assist-row">
            <span class="field-hint">至少 20 个字，建议写 2–3 段。</span>
            <button type="button" class="ai-assist-btn" data-ai-polish>${icon('sparkles')} AI 润色</button>
          </div>
          <span class="field-error" data-error-for="bio"></span>
        </label>
      </div>

      <div class="form-section">
        <div class="form-section-head">
          <span class="form-step">02</span>
          <div><h2>你擅长带人怎么玩</h2><p>选你真正喜欢、也做得来的，不用全都选。</p></div>
        </div>
        <div class="choice-grid" data-service-choices>
          ${(meta.serviceTypes || [])
            .map(
              (service) => `
            <label class="choice-card">
              <input type="checkbox" name="services" value="${escapeHTML(service)}">
              <span class="choice-icon">${icon(SERVICE_META[service]?.icon || 'sparkles')}</span>
              <span class="choice-copy"><strong>${escapeHTML(service)}</strong><small>${escapeHTML(SERVICE_META[service]?.note || '')}</small></span>
              <span class="choice-check">${icon('check')}</span>
            </label>`
            )
            .join('')}
        </div>
        <span class="field-error" data-error-for="services"></span>

        <div class="form-subgroup">
          <span class="field-label">可以沟通的语言 <em>*</em></span>
          <div class="chip-checks">
            ${(meta.languages || [])
              .map(
                (language) => `<label class="chip-check"><input type="checkbox" name="languages" value="${escapeHTML(language)}" ${language === '中文' ? 'checked' : ''}><span>${escapeHTML(language)}</span></label>`
              )
              .join('')}
          </div>
          <span class="field-error" data-error-for="languages"></span>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-head">
          <span class="form-step">03</span>
          <div><h2>价格与封面</h2><p>价格可以随时调整，先从一个让你舒服的数字开始。</p></div>
        </div>
        <label class="field field--price">
          <span class="field-label">半日基础价（4 小时）<em>*</em></span>
          <span class="price-input">
            <span>¥</span>
            <input type="number" name="price" min="50" max="3000" step="1" placeholder="268" inputmode="numeric">
            <small>元 / 半天起</small>
          </span>
          <span class="field-hint">全天套餐会按基础价自动生成，之后可以再调整。平台不收取发布费用。</span>
          <span class="field-error" data-error-for="price"></span>
        </label>

        <div class="form-subgroup">
          <span class="field-label">选择一张封面 <em>*</em></span>
          <div class="cover-upload-bar">
            <button type="button" class="btn btn--soft btn--sm cover-upload-btn" data-cover-upload>${icon('upload')} 从本地导入封面</button>
            <span>${icon('image')} 支持 JPG / PNG / WebP，上传后自动压缩</span>
          </div>
          <div class="cover-picker" data-cover-picker>
            ${covers
              .map(
                (cover, index) => `
              <label class="cover-choice">
                <input type="radio" name="cover" value="${escapeHTML(cover.value)}" ${index === 0 ? 'checked' : ''}>
                <img src="${escapeHTML(cover.value)}" alt="${escapeHTML(cover.label)}" loading="lazy">
                <span class="cover-choice-label">${escapeHTML(cover.label)}</span>
                <span class="cover-choice-check">${icon('check')}</span>
              </label>`
              )
              .join('')}
          </div>
          <input type="file" accept="image/*" data-cover-file hidden>
          <span class="field-hint">可以直接从本地相册导入一张照片，上传后会自动压缩并同步预览。</span>
          <span class="field-error" data-error-for="cover"></span>
        </div>

        <div class="form-subgroup">
          <span class="field-label">头像底色</span>
          <div class="avatar-tone-row">
            <div class="tone-picker">
              ${tones
                .map(
                  (tone, index) => `
                <label class="tone-choice">
                  <input type="radio" name="avatarTone" value="${escapeHTML(tone)}" ${tone === (user.avatarTone || 'sage') || (!user.avatarTone && index === 0) ? 'checked' : ''}>
                  <span class="avatar avatar--md avatar--${escapeHTML(tone)}">禾</span>
                </label>`
                )
                .join('')}
            </div>
            <div class="avatar-upload-controls">
              <span class="avatar-current" data-become-avatar-preview>${avatar(user.name, user.avatarTone, 'md', user.avatarUrl)}</span>
              <button type="button" class="btn btn--ghost btn--sm" data-become-avatar-upload>${icon('camera')} ${user.avatarUrl ? '更换本地头像' : '上传本地头像'}</button>
              <button type="button" class="text-link" data-become-avatar-remove ${user.avatarUrl ? '' : 'hidden'}>移除本地头像</button>
              <input type="file" accept="image/*" data-become-avatar-file hidden>
            </div>
          </div>
          <span class="field-hint" data-avatar-hint>${user.avatarUrl ? '已使用本地头像，将以照片优先展示。' : '上传一张本地照片作为头像，或使用昵称首字的底色头像。'}</span>
        </div>
      </div>

      <div class="form-section form-section--submit">
        <label class="checkline form-agree">
          <input type="checkbox" name="agree">
          <span>我确认以上信息真实，并愿意遵守青禾社区公约：公开场所见面、平台内沟通、拒绝私下交易与任何越界邀约。</span>
        </label>
        <span class="field-error" data-error-for="agree"></span>
        <div class="submit-row">
          <div><strong>准备好被旅人看见了？</strong><span>发布后即可在「找地陪」中展示。</span></div>
          <button type="submit" class="btn btn--primary btn--lg" data-publish>发布我的地陪服务 ${icon('arrow-right')}</button>
        </div>
      </div>
    </form>`;
}

function previewShell(user) {
  return `
    <div class="preview-panel" data-preview>
      <div class="preview-head">
        <span class="eyebrow">LIVE PREVIEW</span>
        <span class="preview-live"><i></i> 实时预览</span>
      </div>
      <div class="preview-card">
        <div class="preview-cover">
          <img src="/assets/images/guide-shanghai.jpg" alt="" data-preview-cover>
          <span class="media-badge">${icon('leaf')} 新入驻</span>
        </div>
        <div class="preview-body">
          <div class="preview-identity">
            ${avatar(user.name, user.avatarTone, 'md', user.avatarUrl)}
            <div><strong data-preview-name>${escapeHTML(user.name)}</strong><span data-preview-city>你的城市</span></div>
            <span class="preview-price" data-preview-price>¥—<small>/半天</small></span>
          </div>
          <p class="preview-headline" data-preview-headline>用一句话告诉旅人，和你一起逛会是什么感觉。</p>
          <div class="tag-row" data-preview-tags><span class="tag tag--muted">等待选择服务</span></div>
          <div class="preview-foot">
            <span>${icon('star')} 新朋友</span>
            <span>${icon('clock')} 24 小时内回复</span>
          </div>
        </div>
      </div>
      <div class="preview-tips">
        <h3>${icon('sparkles')} 让服务更容易被选中</h3>
        <ul>
          <li>${icon('check')} 封面选择你熟悉的真实场景</li>
          <li>${icon('check')} 一句话写清楚你的不同</li>
          <li>${icon('check')} 价格从一次轻松的半天开始</li>
        </ul>
      </div>
      <div class="preview-note">
        <span>${icon('shield')}</span>
        <p>发布后，你可以随时在「我的服务」里暂停接单。新入驻地陪会显示「新朋友」标识，完成首次服务后可申请本地人认证。</p>
      </div>
    </div>`;
}

export function renderBecome(root) {
  setPageTitle('成为地陪');
  const meta = appState.meta;
  const user = session.user;

  root.innerHTML = `
    <section class="become-hero">
      <div class="become-hero-orb" aria-hidden="true"></div>
      <div class="container become-hero-grid">
        <div class="become-hero-copy">
          <nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><span>成为地陪</span></nav>
          <span class="eyebrow">BECOME A LOCAL HOST</span>
          <h1>把你的城市，<br>讲给<span class="marker">旅人听<svg viewBox="0 0 180 18" preserveAspectRatio="none" aria-hidden="true"><path d="M3 12C50 4 120 3 177 9" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></span>。</h1>
          <p>不用辞职，也不用全天在线。把你熟悉的街巷、常去的店和这座城市的脾气，变成一份时间自由的副业。</p>
          <div class="become-hero-actions">
            <button type="button" class="btn btn--primary btn--lg" data-scroll-form>开始发布 ${icon('arrow-down')}</button>
            <a class="btn btn--text btn--lg" href="/guides/g_linxiaoman">看看别人的服务 ${icon('arrow-up-right')}</a>
          </div>
          <div class="become-stats">
            <div><strong>0</strong><span>押金 / 入驻费</span></div>
            <i></i>
            <div><strong>¥200+</strong><span>半日收入参考</span></div>
            <i></i>
            <div><strong>自由</strong><span>接单时间自己定</span></div>
          </div>
        </div>
        <div class="become-hero-visual">
          <div class="earnings-card">
            <div class="earnings-head"><span>本月预计收入</span><span class="earnings-badge">${icon('leaf')} 时间自由</span></div>
            <strong class="earnings-value">¥ 3,680<span>.00</span></strong>
            <div class="earnings-chart" aria-hidden="true">
              <i style="--h: 28%"></i><i style="--h: 45%"></i><i style="--h: 36%"></i><i style="--h: 62%"></i><i style="--h: 50%"></i><i style="--h: 78%"></i><i style="--h: 92%"></i>
            </div>
            <div class="earnings-foot"><span>本月 8 次陪伴</span><span class="earnings-up">${icon('arrow-up-right')} 28%</span></div>
          </div>
          <div class="become-note-card become-note-card--one">
            <span>${icon('calendar')}</span>
            <div><strong>周六 · 10:00</strong><span>梧桐区半日漫步</span></div>
            <span class="mini-status">已确认</span>
          </div>
          <div class="become-note-card become-note-card--two">
            <span class="mini-star">${icon('star')}</span>
            <div><strong>新评价</strong><span>“像朋友一样，很松弛。”</span></div>
          </div>
          <span class="become-sticker">LOCAL<br>HOST</span>
        </div>
      </div>
    </section>

    <section class="become-body">
      <div class="container">
        <div class="become-process">
          <div class="process-item"><span>01</span><div><strong>写下真实的你</strong><p>城市、路线、节奏，5 分钟填完。</p></div></div>
          <div class="process-line"></div>
          <div class="process-item"><span>02</span><div><strong>预览并发布</strong><p>实时看到旅人眼中的样子。</p></div></div>
          <div class="process-line"></div>
          <div class="process-item"><span>03</span><div><strong>等待第一次见面</strong><p>预约确认、沟通、出发。</p></div></div>
        </div>

        ${
          user
            ? `<div class="become-layout">
                <div class="become-form-wrap">
                  <div class="become-form-head">
                    <span class="eyebrow">YOUR LOCAL PROFILE</span>
                    <h2>让旅人认识你</h2>
                    <p>以下信息会展示在你的地陪详情页。带 <em>*</em> 的为必填项。</p>
                  </div>
                  ${formShell(user, meta)}
                </div>
                ${previewShell(user)}
              </div>`
            : gateShell(user)
        }
      </div>
    </section>

    <section class="section section--become-bottom">
      <div class="container">
        <div class="become-faq">
          <div><span class="eyebrow">BEFORE YOU START</span><h2>关于这份副业，<br>你可能想知道</h2></div>
          <div class="faq-list">
            <details open><summary>需要每天在线吗？<span>${icon('plus')}</span></summary><p>不需要。你可以随时在个人中心暂停接单。预约会先发到你的账户，确认合适再接。</p></details>
            <details><summary>平台会收取费用吗？<span>${icon('plus')}</span></summary><p>当前演示版不收取发布费用。正式版本会在服务完成后收取少量平台服务费，并提前公示。</p></details>
            <details><summary>安全怎么保障？<span>${icon('plus')}</span></summary><p>我们鼓励公开场所见面、平台内沟通和提前确认行程。所有预约都会留痕，遇到问题可随时反馈。</p></details>
          </div>
        </div>
      </div>
    </section>`;

  const loginButton = root.querySelector('[data-gate-login]');
  loginButton?.addEventListener('click', async () => {
    const loggedIn = await openAuthModal({ mode: 'register', reason: '注册后就可以发布你的第一条地陪服务。' });
    if (loggedIn) renderBecome(root);
  });

  root.querySelector('[data-scroll-form]')?.addEventListener('click', () => {
    const target = root.querySelector('[data-become-form]') || root.querySelector('.become-gate');
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (!session.user) toast('先登录，再开始填写你的服务', 'info');
  });

  initReveals(root);
  if (!user) return;

  const form = root.querySelector('[data-become-form]');
  const preview = root.querySelector('[data-preview]');
  const publishButton = root.querySelector('[data-publish]');

  const counters = () => {
    ['headline', 'bio'].forEach((name) => {
      const input = form.elements[name];
      const holder = form.querySelector(`[data-counter-for="${name}"]`);
      if (input && holder) holder.textContent = `${Array.from(input.value).length} / ${name === 'headline' ? 40 : 600}`;
    });
  };

  const selectedValues = (name) => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map((input) => input.value);

  const updatePreview = () => {
    const name = form.elements.name.value.trim() || session.user.name;
    const city = form.elements.city.value;
    const headline = form.elements.headline.value.trim();
    const price = form.elements.price.value;
    const services = selectedValues('services');
    const cover = form.querySelector('input[name="cover"]:checked')?.value || '/assets/images/guide-shanghai.jpg';
    const tone = form.querySelector('input[name="avatarTone"]:checked')?.value || 'sage';

    preview.querySelector('[data-preview-name]').textContent = name;
    preview.querySelector('[data-preview-city]').textContent = city ? `${city} · 本地搭子` : '你的城市';
    preview.querySelector('[data-preview-headline]').textContent = headline || '用一句话告诉旅人，和你一起逛会是什么感觉。';
    preview.querySelector('[data-preview-price]').innerHTML = price ? `${money(price)}<small>/半天</small>` : '¥—<small>/半天</small>';
    preview.querySelector('[data-preview-cover]').src = cover;
    preview.querySelector('.preview-identity .avatar').outerHTML = avatar(name, tone, 'md', session.user.avatarUrl);
    preview.querySelector('[data-preview-tags]').innerHTML = services.length
      ? services.slice(0, 3).map((service) => `<span class="tag">${escapeHTML(service)}</span>`).join('')
      : '<span class="tag tag--muted">等待选择服务</span>';
  };

  const setError = (name, message) => {
    const holder = form.querySelector(`[data-error-for="${name}"]`);
    if (holder) holder.textContent = message || '';
    const field = form.querySelector(`[name="${name}"]`);
    if (field) field.classList.toggle('is-invalid', Boolean(message));
  };

  const clearErrors = () => {
    form.querySelectorAll('.field-error').forEach((el) => (el.textContent = ''));
    form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
  };

  const validate = () => {
    clearErrors();
    const name = form.elements.name.value.trim();
    const city = form.elements.city.value;
    const headline = form.elements.headline.value.trim();
    const bio = form.elements.bio.value.trim();
    const price = Number(form.elements.price.value);
    const services = selectedValues('services');
    const languages = selectedValues('languages');
    const cover = form.querySelector('input[name="cover"]:checked')?.value;
    const agree = form.elements.agree.checked;

    if (Array.from(name).length < 2 || Array.from(name).length > 12) return setError('name', '接单昵称需要 2–12 个字符'), false;
    if (!city) return setError('city', '请选择你生活的城市'), false;
    if (Array.from(headline).length < 6) return setError('headline', '一句话介绍至少 6 个字符'), false;
    if (Array.from(bio).length < 20) return setError('bio', '个人介绍至少写 20 个字'), false;
    if (!services.length) return setError('services', '请至少选择一种服务类型'), false;
    if (!languages.length) return setError('languages', '请至少选择一种沟通语言'), false;
    if (!Number.isFinite(price) || price < 50 || price > 3000) return setError('price', '价格需要在 ¥50–¥3000 之间'), false;
    if (!cover) return setError('cover', '请选择一张封面图'), false;
    if (!agree) return setError('agree', '请先阅读并同意社区公约'), false;
    return true;
  };

  const coverFileInput = form.querySelector('[data-cover-file]');
  const coverUploadTile = form.querySelector('[data-cover-upload]');
  const coverPicker = form.querySelector('[data-cover-picker]');
  let uploadingCover = false;

  const setCoverUploadBusy = (busy) => {
    uploadingCover = busy;
    coverUploadTile.disabled = busy;
    coverUploadTile.classList.toggle('is-busy', busy);
    coverUploadTile.innerHTML = busy
      ? `<span class="spinner"></span> 正在导入…`
      : `${icon('upload')} ${coverPicker.querySelector('[data-custom-cover]') ? '重新导入封面' : '从本地导入封面'}`;
  };

  coverUploadTile.addEventListener('click', () => {
    if (!uploadingCover) coverFileInput.click();
  });

  coverFileInput.addEventListener('change', async () => {
    const file = coverFileInput.files?.[0];
    if (!file) return;
    setCoverUploadBusy(true);
    setError('cover', '');
    try {
      const dataUrl = await compressImageFile(file, { maxSize: 1600 });
      const result = await api('/api/uploads', { method: 'POST', body: { kind: 'guide-cover', dataUrl } });
      let customCover = coverPicker.querySelector('[data-custom-cover]');
      if (!customCover) {
        customCover = document.createElement('label');
        customCover.className = 'cover-choice cover-choice--custom';
        customCover.dataset.customCover = 'true';
        customCover.innerHTML = `
          <input type="radio" name="cover" data-custom-cover-input>
          <img alt="我导入的封面" loading="lazy">
          <span class="cover-choice-label">我的照片</span>
          <span class="cover-choice-check">${icon('check')}</span>`;
        coverPicker.prepend(customCover);
      }
      const input = customCover.querySelector('input');
      input.value = result.url;
      input.checked = true;
      customCover.querySelector('img').src = result.url;
      updatePreview();
      toast('封面照片已导入，并自动压缩');
    } catch (error) {
      toast(error instanceof Error ? error.message : '封面导入失败，请稍后再试', 'error');
    } finally {
      setCoverUploadBusy(false);
      coverFileInput.value = '';
    }
  });

  const avatarUploadButton = form.querySelector('[data-become-avatar-upload]');
  const avatarRemoveButton = form.querySelector('[data-become-avatar-remove]');
  const avatarFileInput = form.querySelector('[data-become-avatar-file]');
  const avatarHint = form.querySelector('[data-avatar-hint]');
  let uploadingAvatar = false;

  const syncAvatarControls = (currentUser) => {
    const hasPhoto = Boolean(currentUser.avatarUrl);
    const avatarPreview = form.querySelector('[data-become-avatar-preview]');
    if (avatarPreview) avatarPreview.innerHTML = avatar(currentUser.name, currentUser.avatarTone, 'md', currentUser.avatarUrl);
    avatarUploadButton.innerHTML = `${icon('camera')} ${hasPhoto ? '更换本地头像' : '上传本地头像'}`;
    avatarRemoveButton.hidden = !hasPhoto;
    avatarHint.textContent = hasPhoto
      ? '已使用本地头像，将以照片优先展示。'
      : '上传一张本地照片作为头像，或使用昵称首字的底色头像。';
  };

  avatarUploadButton.addEventListener('click', () => {
    if (!uploadingAvatar) avatarFileInput.click();
  });

  avatarFileInput.addEventListener('change', async () => {
    const file = avatarFileInput.files?.[0];
    if (!file) return;
    uploadingAvatar = true;
    avatarUploadButton.disabled = true;
    avatarUploadButton.innerHTML = '<span class="spinner"></span> 正在上传…';
    try {
      const dataUrl = await compressImageFile(file, { maxSize: 720, square: true });
      const result = await api('/api/profile/photo', { method: 'POST', body: { kind: 'avatar', dataUrl } });
      updateSessionUser(result.user);
      syncAvatarControls(result.user);
      updatePreview();
      toast('本地头像已更新');
    } catch (error) {
      toast(error instanceof Error ? error.message : '头像上传失败，请稍后再试', 'error');
    } finally {
      uploadingAvatar = false;
      avatarUploadButton.disabled = false;
      avatarFileInput.value = '';
      syncAvatarControls(session.user);
    }
  });

  avatarRemoveButton.addEventListener('click', async () => {
    if (uploadingAvatar) return;
    uploadingAvatar = true;
    avatarRemoveButton.disabled = true;
    try {
      const result = await api('/api/profile/photo', { method: 'DELETE', body: { kind: 'avatar' } });
      updateSessionUser(result.user);
      syncAvatarControls(result.user);
      updatePreview();
      toast('已恢复为底色头像', 'info');
    } catch (error) {
      toast(error instanceof Error ? error.message : '头像移除失败，请稍后再试', 'error');
    } finally {
      uploadingAvatar = false;
      avatarRemoveButton.disabled = false;
    }
  });

  form.querySelector('[data-ai-polish]')?.addEventListener('click', () => {
    openPolishModal({
      text: form.elements.bio.value,
      scene: 'guide',
      city: form.elements.city.value,
      onApply: (value) => {
        form.elements.bio.value = value;
        form.elements.bio.dispatchEvent(new Event('input', { bubbles: true }));
        form.elements.bio.focus();
      }
    });
  });

  form.addEventListener('input', (event) => {
    if (event.target.name) setError(event.target.name, '');
    counters();
    updatePreview();
  });
  form.addEventListener('change', () => {
    counters();
    updatePreview();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!validate()) {
      const firstError = form.querySelector('.field-error:not(:empty)');
      firstError?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    publishButton.disabled = true;
    const original = publishButton.innerHTML;
    publishButton.innerHTML = '<span class="spinner"></span><span>正在发布…</span>';

    try {
      const payload = {
        name: form.elements.name.value.trim(),
        city: form.elements.city.value,
        headline: form.elements.headline.value.trim(),
        bio: form.elements.bio.value.trim(),
        price: Number(form.elements.price.value),
        cover: form.querySelector('input[name="cover"]:checked').value,
        avatarTone: form.querySelector('input[name="avatarTone"]:checked')?.value || session.user.avatarTone,
        services: selectedValues('services'),
        languages: selectedValues('languages')
      };
      const { guide } = await api('/api/guides', { method: 'POST', body: payload });
      toast('发布成功，旅人已经可以看到你的服务了');
      navigate(`/guides/${encodeURIComponent(guide.id)}`);
    } catch (error) {
      if (error instanceof ApiError) {
        setError(error.field || '', error.message);
        const target = error.field ? form.querySelector(`[name="${error.field}"]`) : null;
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      toast(error instanceof ApiError ? error.message : '发布没有成功，请稍后再试', 'error');
      publishButton.disabled = false;
      publishButton.innerHTML = original;
    }
  });

  counters();
  updatePreview();
}
