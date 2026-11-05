import { avatar, escapeHTML, icon, isFavorite, money } from '../ui.js?v=1.7.0';

export function guideCard(guide) {
  const saved = isFavorite(guide.id);
  const badge = guide.isOwner
    ? '<span class="media-badge media-badge--owner">' + icon('user') + ' 我发布的</span>'
    : guide.verified
      ? '<span class="media-badge">' + icon('shield') + ' 本地人认证</span>'
      : '<span class="media-badge media-badge--new">' + icon('leaf') + ' 新入驻</span>';
  const ratingText = guide.reviewCount
    ? `${Number(guide.rating).toFixed(1)} <span>· ${guide.reviewCount} 条</span>`
    : '<span>新朋友 · 暂无评价</span>';

  return `
    <article class="guide-card reveal" data-guide-card="${escapeHTML(guide.id)}">
      <div class="guide-card-media">
        <a href="/guides/${encodeURIComponent(guide.id)}" class="guide-card-image-link" aria-label="查看 ${escapeHTML(guide.name)} 的地陪服务">
          <img src="${escapeHTML(guide.cover)}" alt="${escapeHTML(guide.city)} · ${escapeHTML(guide.name)} 的地陪路线" loading="lazy">
        </a>
        ${badge}
        <button class="favorite-btn ${saved ? 'is-saved' : ''}" type="button" data-favorite="${escapeHTML(guide.id)}"
          aria-label="${saved ? '取消收藏' : '收藏这位地陪'}" aria-pressed="${saved}">
          ${icon('heart')}
        </button>
        <div class="media-location">${icon('pin')} ${escapeHTML(guide.city)}</div>
      </div>
      <div class="guide-card-body">
        <div class="guide-card-heading">
          <div class="guide-card-name">
            ${avatar(guide.name, guide.avatarTone, 'sm', guide.avatarUrl)}
            <div>
              <h3><a href="/guides/${encodeURIComponent(guide.id)}">${escapeHTML(guide.name)}</a></h3>
              <p>${escapeHTML(guide.city)} · ${Number(guide.orders) || 0} 次陪伴</p>
            </div>
          </div>
          <div class="rating-badge" title="旅人评分">${icon('star')} <span>${ratingText}</span></div>
        </div>
        <p class="guide-card-tagline">${escapeHTML(guide.headline)}</p>
        <div class="tag-row">
          ${(guide.tags || []).slice(0, 3).map((tag) => `<span class="tag">${escapeHTML(tag)}</span>`).join('')}
        </div>
        <div class="guide-card-foot">
          <p class="price"><span class="price-from">${money(guide.price)}</span><span class="price-unit">/ 半天起</span></p>
          <div class="guide-card-actions">
            ${guide.isOwner ? '' : `<button type="button" class="card-chat-btn" data-chat-guide="${escapeHTML(guide.id)}">${icon('message')} 私聊</button>`}
            <a class="card-cta" href="/guides/${encodeURIComponent(guide.id)}">看看路线 ${icon('arrow-up-right')}</a>
          </div>
        </div>
      </div>
    </article>`;
}

export function guideCardSkeleton() {
  return `
    <div class="guide-card guide-card--skeleton" aria-hidden="true">
      <div class="skeleton skeleton-media"></div>
      <div class="guide-card-body">
        <div class="skeleton skeleton-line skeleton-line--short"></div>
        <div class="skeleton skeleton-line"></div>
        <div class="skeleton skeleton-line skeleton-line--medium"></div>
        <div class="skeleton skeleton-line skeleton-line--short"></div>
      </div>
    </div>`;
}
