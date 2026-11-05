import { api, ApiError } from '../api.js?v=1.7.0';
import { openAuthModal } from '../components/auth-modal.js?v=1.7.0';
import { navigate } from '../router.js?v=1.7.0';
import { openPolishModal } from '../components/ai-polish.js?v=1.7.0';
import { compressImageFile } from '../image.js?v=1.7.0';
import { session, updateSessionUser } from '../session.js?v=1.7.0';
import { appState } from '../state.js?v=1.7.0';
import {
  avatar,
  cityOptionsHTML,
  confirmDialog,
  escapeHTML,
  icon,
  initReveals,
  joinedDate,
  setPageTitle,
  toast
} from '../ui.js?v=1.7.0';

const MAX_PHOTOS = 6;

function gateShell() {
  return `
    <section class="account-gate">
      <div class="account-gate-card">
        <div class="account-gate-visual">
          <span class="gate-mark">${icon('user')}</span>
          <span class="account-gate-line"></span>
          <span class="account-gate-route">${icon('image')}</span>
        </div>
        <div>
          <span class="eyebrow">YOUR PROFILE</span>
          <h1>登录后，<br>把故事放在照片里。</h1>
          <p>上传一张喜欢的城市照片作为封面，再给自己选一个清楚的头像。你的个人资料会更有温度。</p>
          <button type="button" class="btn btn--primary btn--lg" data-profile-login>登录 / 注册 ${icon('arrow-right')}</button>
        </div>
      </div>
    </section>`;
}

function completion(user) {
  const checks = [Boolean(user.name), Boolean(user.city), Boolean(user.bio), Boolean(user.avatarUrl), Boolean(user.coverUrl), (user.photos || []).length > 0];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function coverStyle(user) {
  return user.coverUrl ? `style="--profile-cover:url('${escapeHTML(user.coverUrl)}')"` : '';
}

function galleryMarkup(user) {
  const photos = Array.isArray(user.photos) ? user.photos : [];
  const photoCards = photos
    .map(
      (photo, index) => `
      <div class="profile-photo">
        <img src="${escapeHTML(photo)}" alt="我的照片 ${index + 1}" loading="lazy">
        <button type="button" class="profile-photo-delete" data-delete-photo="${escapeHTML(photo)}" aria-label="删除这张照片">${icon('close')}</button>
      </div>`
    )
    .join('');
  const uploader =
    photos.length < MAX_PHOTOS
      ? `<button type="button" class="profile-photo-add" data-upload-trigger="gallery">
          ${icon('plus')}
          <span>上传本地照片</span>
          <small>${photos.length} / ${MAX_PHOTOS}</small>
        </button>`
      : '';
  return `${photoCards}${uploader}`;
}

function pageShell(user) {
  const percent = completion(user);
  return `
    <div class="container profile-container">
      <nav class="breadcrumb profile-breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><a href="/account">我的青禾</a><span>/</span><span>个人资料</span></nav>

      <section class="profile-cover-card">
        <div class="profile-cover ${user.coverUrl ? 'has-image' : ''}" data-profile-cover ${coverStyle(user)}>
          <span class="profile-cover-shade" aria-hidden="true"></span>
          <div class="profile-cover-actions">
            <button type="button" class="btn btn--light btn--sm" data-upload-trigger="cover">${icon('upload')} ${user.coverUrl ? '更换封面' : '上传封面'}</button>
            <button type="button" class="btn btn--ghost btn--sm profile-remove-btn" data-remove-media="cover" ${user.coverUrl ? '' : 'hidden'}>移除</button>
          </div>
          <div class="profile-cover-copy">
            <span>${icon('image')} ${user.coverUrl ? '我的城市封面' : '一张你喜欢的城市照片'}</span>
            <small>${user.coverUrl ? '来自本地相册 · 可随时更换' : 'JPEG / PNG / WebP · 建议横向构图'}</small>
          </div>
        </div>
        <div class="profile-head">
          <div class="profile-avatar-wrap">
            <div class="profile-avatar" data-profile-avatar>
              ${avatar(user.name, user.avatarTone, 'xl', user.avatarUrl)}
              <button type="button" class="profile-avatar-upload" data-upload-trigger="avatar" aria-label="上传头像">${icon('camera')}</button>
            </div>
            <div class="profile-avatar-actions">
              <button type="button" data-upload-trigger="avatar">更换头像</button>
              <button type="button" data-remove-media="avatar" ${user.avatarUrl ? '' : 'hidden'}>移除</button>
            </div>
          </div>
          <div class="profile-head-copy">
            <span class="eyebrow">MY PROFILE</span>
            <h1>${escapeHTML(user.name)}</h1>
            <p>${user.city ? `${icon('pin')} ${escapeHTML(user.city)}` : `${icon('pin')} 还没选择常驻城市`} <span class="dot-sep"></span> ${joinedDate(user.joinedAt)}</p>
          </div>
          <a class="btn btn--ghost profile-back" href="/account">${icon('arrow-left')} 返回我的青禾</a>
        </div>
      </section>

      <div class="profile-layout">
        <div class="profile-main">
          <section class="profile-card">
            <div class="profile-card-head">
              <div><span class="eyebrow">BASIC INFO</span><h2>基本信息</h2></div>
              <span class="section-side-note">${icon('user')} 展示在个人中心</span>
            </div>
            <form class="profile-form" data-profile-form novalidate>
              <div class="form-grid form-grid--two">
                <label class="field">
                  <span class="field-label">昵称</span>
                  <span class="input-wrap input-wrap--plain"><input type="text" name="name" maxlength="16" value="${escapeHTML(user.name)}" placeholder="怎么称呼你"></span>
                  <span class="field-error" data-error-for="name"></span>
                </label>
                <label class="field">
                  <span class="field-label">常驻城市</span>
                  <span class="input-wrap input-wrap--plain">
                    <select name="city">${cityOptionsHTML(appState.meta?.cityGroups, user.city, { allLabel: '选择常驻城市' })}</select>
                  </span>
                  <span class="field-error" data-error-for="city"></span>
                </label>
              </div>
              <label class="field">
                <span class="field-label">个人简介 <small data-bio-counter>${Array.from(user.bio || '').length} / 160</small></span>
                <span class="input-wrap input-wrap--plain">
                  <textarea name="bio" rows="4" maxlength="160" placeholder="用一两句话介绍自己，比如喜欢的城市角落、旅行方式。">${escapeHTML(user.bio || '')}</textarea>
                </span>
                <div class="ai-assist-row">
                  <span class="field-hint">简介会出现在个人中心，不会公开展示给其他旅人。</span>
                  <button type="button" class="ai-assist-btn" data-ai-polish>${icon('sparkles')} AI 润色</button>
                </div>
                <span class="field-error" data-error-for="bio"></span>
              </label>
              <div class="profile-form-foot">
                <span>${icon('lock')} 资料只会用于你的青禾账号</span>
                <button type="submit" class="btn btn--primary" data-save-profile>保存资料 ${icon('check')}</button>
              </div>
            </form>
          </section>

          <section class="profile-card">
            <div class="profile-card-head">
              <div><span class="eyebrow">PHOTO WALL</span><h2>我的照片</h2></div>
              <span class="profile-photo-count">${(user.photos || []).length} / ${MAX_PHOTOS}</span>
            </div>
            <p class="profile-card-lead">从本地相册上传一些你喜欢的城市瞬间。它们只会出现在你的个人资料里。</p>
            <div class="profile-gallery" data-profile-gallery>${galleryMarkup(user)}</div>
            <div class="profile-upload-note">
              ${icon('shield')}
              <span>照片保存在本机演示项目中，不会上传到第三方服务。单张不超过 15MB，自动压缩为最长边 1600px。</span>
            </div>
          </section>
        </div>

        <aside class="profile-aside">
          <div class="profile-preview-card">
            <span class="eyebrow">PROFILE PREVIEW</span>
            <div class="profile-preview-cover ${user.coverUrl ? 'has-image' : ''}" data-profile-preview-cover ${coverStyle(user)}></div>
            <div class="profile-preview-body">
              <div class="profile-preview-avatar">${avatar(user.name, user.avatarTone, 'md', user.avatarUrl)}</div>
              <strong>${escapeHTML(user.name)}</strong>
              <span>${escapeHTML(user.city || '城市待填写')}</span>
              <p>${escapeHTML(user.bio || '写一句个人简介，让这里更像你。')}</p>
            </div>
            <div class="profile-completion">
              <div><span>资料完成度</span><strong>${percent}%</strong></div>
              <div class="profile-completion-bar"><i style="width:${percent}%"></i></div>
            </div>
          </div>
          <div class="profile-aside-note">
            <span>${icon('leaf')}</span>
            <div><strong>让头像先被记住</strong><p>上传头像后，你的头像会同步显示在导航栏和你发布的地陪服务中。</p></div>
          </div>
          <a class="btn btn--soft btn--full" href="/become">${icon('route')} 去发布地陪服务</a>
        </aside>
      </div>
    </div>

    <input type="file" accept="image/*" data-upload-input="avatar" hidden>
    <input type="file" accept="image/*" data-upload-input="cover" hidden>
    <input type="file" accept="image/*" multiple data-upload-input="gallery" hidden>`;
}

export function renderProfile(root, route) {
  setPageTitle('个人资料');
  if (!session.user) {
    root.innerHTML = gateShell();
    root.querySelector('[data-profile-login]')?.addEventListener('click', async () => {
      const user = await openAuthModal({ mode: 'login', reason: '登录后即可编辑资料、上传本地照片。' });
      if (user) renderProfile(root, route);
    });
    return;
  }

  root.innerHTML = pageShell(session.user);
  initReveals(root);

  const form = root.querySelector('[data-profile-form]');
  const bioInput = form.elements.bio;
  const bioCounter = root.querySelector('[data-bio-counter]');
  const saveButton = root.querySelector('[data-save-profile]');
  let uploading = false;

  const setError = (name, message) => {
    const holder = form.querySelector(`[data-error-for="${name}"]`);
    if (holder) holder.textContent = message || '';
    const field = form.elements[name];
    if (field) field.classList.toggle('is-invalid', Boolean(message));
  };

  const syncMedia = (user) => {
    const avatarHolder = root.querySelector('[data-profile-avatar]');
    if (avatarHolder) avatarHolder.querySelector('.avatar').outerHTML = avatar(user.name, user.avatarTone, 'xl', user.avatarUrl);

    const cover = root.querySelector('[data-profile-cover]');
    if (cover) {
      cover.classList.toggle('has-image', Boolean(user.coverUrl));
      cover.style.setProperty('--profile-cover', user.coverUrl ? `url('${user.coverUrl}')` : 'none');
      const trigger = cover.querySelector('[data-upload-trigger="cover"]');
      if (trigger) trigger.innerHTML = `${icon('upload')} ${user.coverUrl ? '更换封面' : '上传封面'}`;
      const remove = cover.querySelector('[data-remove-media="cover"]');
      if (remove) remove.hidden = !user.coverUrl;
    }

    const avatarRemove = root.querySelector('[data-remove-media="avatar"]');
    if (avatarRemove) avatarRemove.hidden = !user.avatarUrl;

    const previewCover = root.querySelector('[data-profile-preview-cover]');
    if (previewCover) {
      previewCover.classList.toggle('has-image', Boolean(user.coverUrl));
      previewCover.style.setProperty('--profile-cover', user.coverUrl ? `url('${user.coverUrl}')` : 'none');
    }
    const previewAvatar = root.querySelector('.profile-preview-avatar');
    if (previewAvatar) previewAvatar.innerHTML = avatar(user.name, user.avatarTone, 'md', user.avatarUrl);
    const completionValue = completion(user);
    const completionText = root.querySelector('.profile-completion strong');
    if (completionText) completionText.textContent = `${completionValue}%`;
    const completionBar = root.querySelector('.profile-completion-bar i');
    if (completionBar) completionBar.style.width = `${completionValue}%`;
  };

  const bindGallery = () => {
    const gallery = root.querySelector('[data-profile-gallery]');
    if (!gallery) return;
    gallery.querySelectorAll('[data-upload-trigger="gallery"]').forEach((button) => {
      button.addEventListener('click', () => root.querySelector('[data-upload-input="gallery"]').click());
    });
    gallery.querySelectorAll('[data-delete-photo]').forEach((button) => {
      button.addEventListener('click', async () => {
        const photo = button.dataset.deletePhoto;
        const confirmed = await confirmDialog({
          title: '删除这张照片？',
          message: '照片会从你的个人资料和本地演示项目中移除。',
          confirmText: '删除照片',
          danger: true
        });
        if (!confirmed) return;
        try {
          const result = await api('/api/profile/photo', { method: 'DELETE', body: { kind: 'gallery', url: photo } });
          updateSessionUser(result.user);
          syncMedia(result.user);
          gallery.innerHTML = galleryMarkup(result.user);
          bindGallery();
          root.querySelector('.profile-photo-count').textContent = `${result.user.photos.length} / ${MAX_PHOTOS}`;
          toast('照片已删除', 'info');
        } catch (error) {
          toast(error instanceof ApiError ? error.message : '删除失败，请稍后再试', 'error');
        }
      });
    });
  };

  const uploadFiles = async (kind, files) => {
    if (uploading || !files.length) return;
    if (kind === 'gallery' && (session.user.photos || []).length >= MAX_PHOTOS) {
      toast(`最多可以保存 ${MAX_PHOTOS} 张照片`, 'info');
      return;
    }
    uploading = true;
    root.classList.add('is-uploading');
    const selected = kind === 'gallery' ? [...files].slice(0, MAX_PHOTOS - (session.user.photos || []).length) : [files[0]];
    try {
      for (const file of selected) {
        toast('正在处理图片…', 'info');
        const dataUrl = await compressImageFile(file, {
          maxSize: kind === 'cover' ? 1600 : kind === 'avatar' ? 720 : 1400,
          square: kind === 'avatar'
        });
        const result = await api('/api/profile/photo', { method: 'POST', body: { kind, dataUrl } });
        updateSessionUser(result.user);
        syncMedia(result.user);
        if (kind === 'gallery') {
          const gallery = root.querySelector('[data-profile-gallery]');
          gallery.innerHTML = galleryMarkup(result.user);
          bindGallery();
          root.querySelector('.profile-photo-count').textContent = `${result.user.photos.length} / ${MAX_PHOTOS}`;
        }
      }
      toast(kind === 'avatar' ? '头像已更新' : kind === 'cover' ? '封面已更新' : '照片已上传');
    } catch (error) {
      toast(error instanceof Error ? error.message : '上传失败，请稍后再试', 'error');
    } finally {
      uploading = false;
      root.classList.remove('is-uploading');
      root.querySelectorAll('[data-upload-input]').forEach((input) => {
        input.value = '';
      });
    }
  };

  root.querySelectorAll('[data-upload-trigger]').forEach((button) => {
    button.addEventListener('click', () => {
      if (uploading) return;
      const kind = button.dataset.uploadTrigger;
      if (kind === 'gallery') return;
      root.querySelector(`[data-upload-input="${kind}"]`)?.click();
    });
  });
  bindGallery();

  root.querySelectorAll('[data-upload-input]').forEach((input) => {
    input.addEventListener('change', () => uploadFiles(input.dataset.uploadInput, input.files));
  });

  root.querySelectorAll('[data-remove-media]').forEach((button) => {
    button.addEventListener('click', async () => {
      const kind = button.dataset.removeMedia;
      const confirmed = await confirmDialog({
        title: kind === 'avatar' ? '移除头像？' : '移除封面？',
        message: '移除后将使用青禾默认样式，你可以随时重新上传。',
        confirmText: '确认移除',
        danger: true
      });
      if (!confirmed) return;
      try {
        const result = await api('/api/profile/photo', { method: 'DELETE', body: { kind } });
        updateSessionUser(result.user);
        syncMedia(result.user);
        toast(kind === 'avatar' ? '头像已移除' : '封面已移除', 'info');
      } catch (error) {
        toast(error instanceof ApiError ? error.message : '移除失败，请稍后再试', 'error');
      }
    });
  });

  bioInput.addEventListener('input', () => {
    bioCounter.textContent = `${Array.from(bioInput.value).length} / 160`;
    setError('bio', '');
  });

  root.querySelector('[data-ai-polish]')?.addEventListener('click', () => {
    openPolishModal({
      text: bioInput.value,
      scene: 'profile',
      city: session.user.city || '',
      onApply: (value) => {
        bioInput.value = value;
        bioInput.dispatchEvent(new Event('input', { bubbles: true }));
        bioInput.focus();
      }
    });
  });
  form.elements.name.addEventListener('input', () => setError('name', ''));
  form.elements.city.addEventListener('change', () => setError('city', ''));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = form.elements.name.value.trim();
    const city = form.elements.city.value;
    const bio = form.elements.bio.value.trim();
    setError('name', '');
    setError('bio', '');
    if (Array.from(name).length < 2 || Array.from(name).length > 16) {
      setError('name', '昵称需要 2–16 个字符');
      form.elements.name.focus();
      return;
    }
    if (Array.from(bio).length > 160) {
      setError('bio', '个人简介最多 160 个字');
      return;
    }

    saveButton.disabled = true;
    const original = saveButton.innerHTML;
    saveButton.innerHTML = '<span class="spinner"></span><span>保存中…</span>';
    try {
      const result = await api('/api/profile', { method: 'PATCH', body: { name, city, bio } });
      updateSessionUser(result.user);
      toast('个人资料已保存');
      renderProfile(root, route);
    } catch (error) {
      if (error instanceof ApiError) setError(error.field || '', error.message);
      toast(error instanceof ApiError ? error.message : '保存失败，请稍后再试', 'error');
      saveButton.disabled = false;
      saveButton.innerHTML = original;
    }
  });
}
