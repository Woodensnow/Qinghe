import { api, ApiError } from '../api.js?v=1.7.0';
import { requireAuth } from '../components/auth-modal.js?v=1.7.0';
import { currentUrl, navigate } from '../router.js?v=1.7.0';
import {
  addDays,
  avatar,
  escapeHTML,
  formatDateCN,
  icon,
  initReveals,
  isBookableDate,
  isFavorite,
  localDateISO,
  money,
  readTripDate,
  relativeDateLabel,
  setPageTitle,
  showModal,
  toast,
  toggleFavorite,
  weekdayCN,
  writeTripDate
} from '../ui.js?v=1.7.0';

const TIME_SLOTS = ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];

function starRow(count = 5) {
  return Array.from({ length: 5 }, () => icon('star')).join('');
}

function paragraphs(text) {
  return String(text || '')
    .split(/\n\s*\n/)
    .filter(Boolean)
    .map((part) => `<p>${escapeHTML(part).replaceAll('\n', '<br>')}</p>`)
    .join('');
}

function takeTripDate() {
  const requested = new URLSearchParams(window.location.search).get('date') || '';
  const stored = readTripDate();
  const candidate = requested || stored;
  if (isBookableDate(candidate)) {
    if (requested) writeTripDate(candidate);
    return { date: candidate, rejected: false };
  }
  if (stored && !isBookableDate(stored)) writeTripDate('');
  return { date: localDateISO(addDays(1)), rejected: Boolean(candidate) };
}

function dateChoices(selectedDate) {
  const choices = [];
  for (let i = 1; i <= 12; i += 1) {
    const date = addDays(i);
    const iso = localDateISO(date);
    choices.push({
      iso,
      disabled: false,
      weekday: weekdayCN(iso),
      day: String(date.getDate()).padStart(2, '0'),
      month: date.getMonth() + 1,
      label: relativeDateLabel(iso)
    });
  }
  if (!choices.some((choice) => choice.iso === selectedDate) && isBookableDate(selectedDate)) {
    const date = new Date(`${selectedDate}T12:00:00`);
    if (!Number.isNaN(date.getTime())) {
      choices.unshift({
        iso: selectedDate,
        disabled: false,
        weekday: weekdayCN(selectedDate),
        day: String(date.getDate()).padStart(2, '0'),
        month: date.getMonth() + 1,
        label: relativeDateLabel(selectedDate)
      });
    }
  }
  return choices;
}

function dateChips(selectedDate) {
  return dateChoices(selectedDate)
    .map(
      (choice) => `<button type="button" class="date-chip ${choice.iso === selectedDate ? 'is-active' : ''}" data-date="${escapeHTML(choice.iso)}"
        ${choice.disabled ? 'disabled' : ''} aria-pressed="${choice.iso === selectedDate}">
        <span>${choice.weekday}</span>
        <strong>${choice.day}</strong>
        <small>${choice.month} 月</small>
      </button>`
    )
    .join('');
}

function packageOptions(guide, selectedId) {
  return guide.packages
    .map(
      (pkg) => `
      <label class="package-option ${pkg.id === selectedId ? 'is-selected' : ''}" data-package-option="${escapeHTML(pkg.id)}">
        <input type="radio" name="package" value="${escapeHTML(pkg.id)}" ${pkg.id === selectedId ? 'checked' : ''}>
        <span class="package-radio" aria-hidden="true"></span>
        <span class="package-copy">
          <span class="package-top"><strong>${escapeHTML(pkg.name)}</strong><span class="package-duration">${icon('clock')} ${escapeHTML(pkg.duration)}</span></span>
          <span class="package-desc">${escapeHTML(pkg.description)}</span>
          <span class="package-includes">${(pkg.includes || []).map((item) => `<span>${icon('check')} ${escapeHTML(item)}</span>`).join('')}</span>
        </span>
        <span class="package-price"><strong>${money(pkg.price)}</strong><small>起</small></span>
      </label>`
    )
    .join('');
}

function renderNotFound(root) {
  root.innerHTML = `
    <section class="not-found container">
      <span class="not-found-mark">${icon('compass')}</span>
      <span class="eyebrow">LOST IN THE CITY</span>
      <h1>这位本地搭子好像搬家了</h1>
      <p>页面不存在，或者这位地陪暂时停止了接单。</p>
      <div class="not-found-actions">
        <a class="btn btn--primary" href="/guides">看看其他地陪 ${icon('arrow-right')}</a>
        <a class="btn btn--ghost" href="/">回到首页</a>
      </div>
    </section>`;
}

function openLightbox(images, startIndex = 0) {
  let index = startIndex;
  const body = () => `
    <div class="lightbox">
      <div class="lightbox-stage"><img src="${escapeHTML(images[index])}" alt="地陪路线照片 ${index + 1}"></div>
      <div class="lightbox-foot">
        <div class="lightbox-thumbs">
          ${images
            .map(
              (image, i) =>
                `<button type="button" class="lightbox-thumb ${i === index ? 'is-active' : ''}" data-thumb="${i}" aria-label="查看第 ${i + 1} 张"><img src="${escapeHTML(image)}" alt=""></button>`
            )
            .join('')}
        </div>
        <div class="lightbox-controls">
          <button type="button" class="icon-btn" data-prev aria-label="上一张">${icon('arrow-left')}</button>
          <span>${index + 1} / ${images.length}</span>
          <button type="button" class="icon-btn" data-next aria-label="下一张">${icon('arrow-right')}</button>
        </div>
      </div>
    </div>`;
  const modal = showModal(body(), { className: 'modal--lightbox' });
  const update = () => {
    modal.dialog.innerHTML = `<button class="modal-close" type="button" data-modal-close aria-label="关闭">${icon('close')}</button>${body()}`;
    bind();
  };
  const bind = () => {
    modal.dialog.querySelector('[data-prev]')?.addEventListener('click', () => {
      index = (index - 1 + images.length) % images.length;
      update();
    });
    modal.dialog.querySelector('[data-next]')?.addEventListener('click', () => {
      index = (index + 1) % images.length;
      update();
    });
    modal.dialog.querySelectorAll('[data-thumb]').forEach((button) => {
      button.addEventListener('click', () => {
        index = Number(button.dataset.thumb);
        update();
      });
    });
    modal.dialog.querySelector('[data-modal-close]')?.addEventListener('click', () => modal.close());
  };
  bind();
  const keyHandler = (event) => {
    if (!document.body.contains(modal.backdrop)) {
      document.removeEventListener('keydown', keyHandler);
      return;
    }
    if (event.key === 'ArrowLeft') {
      index = (index - 1 + images.length) % images.length;
      update();
    }
    if (event.key === 'ArrowRight') {
      index = (index + 1) % images.length;
      update();
    }
  };
  document.addEventListener('keydown', keyHandler);
}

function detailShell(guide, selectedDate) {
  const images = (guide.gallery || [guide.cover]).slice(0, 3);
  const selectedPackage = guide.packages[0];
  const saved = isFavorite(guide.id);
  const reviewSummary = guide.reviewCount
    ? `${Number(guide.rating).toFixed(1)} · ${guide.reviewCount} 条评价`
    : '新朋友 · 暂无评价';

  return `
    <div class="container">
      <nav class="breadcrumb detail-breadcrumb" aria-label="面包屑">
        <a href="/">首页</a><span>/</span><a href="/guides">找地陪</a><span>/</span><span>${escapeHTML(guide.city)} · ${escapeHTML(guide.name)}</span>
      </nav>

      <div class="detail-identity">
        <div class="identity-main">
          ${avatar(guide.name, guide.avatarTone, 'xl', guide.avatarUrl)}
          <div class="identity-copy">
            <div class="identity-name-row">
              <h1>${escapeHTML(guide.name)}</h1>
              ${
                guide.verified
                  ? `<span class="verified-pill">${icon('shield')} 本地人认证</span>`
                  : `<span class="verified-pill verified-pill--new">${icon('leaf')} 新入驻</span>`
              }
            </div>
            <p class="identity-headline">${escapeHTML(guide.headline)}</p>
            <div class="identity-meta">
              <span class="identity-rating">${icon('star')} <strong>${Number(guide.rating).toFixed(1)}</strong> <span>${guide.reviewCount ? `${guide.reviewCount} 条评价` : '暂无评价'}</span></span>
              <i></i>
              <span>${icon('pin')} ${escapeHTML(guide.city)}</span>
              <i></i>
              <span>${icon('users')} ${guide.orders} 次陪伴</span>
              <i></i>
              <span>${icon('clock')} ${escapeHTML(guide.responseTime)}</span>
            </div>
          </div>
        </div>
        <div class="identity-actions">
          ${
            guide.isOwner
              ? ''
              : `<button type="button" class="btn btn--soft btn--sm detail-chat-btn" data-chat-guide="${escapeHTML(guide.id)}">${icon('message')} 私聊</button>`
          }
          <button type="button" class="icon-btn icon-btn--bordered ${saved ? 'is-saved' : ''}" data-detail-favorite="${escapeHTML(guide.id)}" aria-label="${saved ? '取消收藏' : '收藏这位地陪'}" aria-pressed="${saved}">
            ${icon('heart')}
          </button>
          <button type="button" class="icon-btn icon-btn--bordered" data-share aria-label="分享这位地陪">${icon('send')}</button>
        </div>
      </div>

      ${
        guide.isOwner
          ? ''
          : `<div class="mobile-booking-bar">
              <div><strong>${money(selectedPackage.price)}</strong><span>/ ${escapeHTML(selectedPackage.duration)}起 · ${Number(guide.rating).toFixed(1)} 分</span></div>
              <button type="button" class="btn btn--primary" data-mobile-scroll>选择日期 ${icon('arrow-right')}</button>
            </div>`
      }

      <div class="detail-layout">
        <div class="detail-main">
          <div class="detail-gallery">
            <button type="button" class="gallery-main" data-lightbox="0" aria-label="查看全部路线照片">
              <img src="${escapeHTML(images[0])}" alt="${escapeHTML(guide.name)} 的${escapeHTML(guide.city)}路线">
              <span class="gallery-count">${icon('camera')} ${images.length} 张照片</span>
            </button>
            <div class="gallery-side">
              ${images
                .slice(1, 3)
                .map(
                  (image, i) => `<button type="button" class="gallery-side-item" data-lightbox="${i + 1}" aria-label="查看照片 ${i + 2}">
                    <img src="${escapeHTML(image)}" alt="" loading="lazy">
                  </button>`
                )
                .join('')}
              <button type="button" class="gallery-more" data-lightbox="0">${icon('sparkles')} 看看这里的日常</button>
            </div>
            <span class="gallery-badge">${icon('pin')} ${escapeHTML(guide.city)} · 本地视角</span>
          </div>

          <div class="identity-tags tag-row">
            ${(guide.tags || []).map((tag) => `<span class="tag tag--soft">${escapeHTML(tag)}</span>`).join('')}
          </div>

          <section class="detail-section about-section">
            <div class="detail-section-head">
              <div><span class="eyebrow">ABOUT YOUR LOCAL</span><h2>关于 ${escapeHTML(guide.name)}</h2></div>
              <span class="section-side-note">${icon('message')} 行前可先沟通</span>
            </div>
            <div class="about-grid">
              <div class="about-copy">${paragraphs(guide.bio)}</div>
              <aside class="about-facts">
                <div class="fact-row"><span>${icon('globe')} 沟通语言</span><strong>${guide.languages.map(escapeHTML).join(' · ')}</strong></div>
                <div class="fact-row"><span>${icon('walk')} 擅长服务</span><strong>${guide.services.map(escapeHTML).join(' · ')}</strong></div>
                <div class="fact-row"><span>${icon('clock')} 平均响应</span><strong>${escapeHTML(guide.responseTime)}</strong></div>
                <div class="fact-row"><span>${icon('check-circle')} 预约确认率</span><strong>${escapeHTML(guide.responseRate)}</strong></div>
              </aside>
            </div>
            <div class="highlights">
              <h3>${icon('sparkles')} 这趟路，你会遇见</h3>
              <ul>${(guide.highlights || []).map((item) => `<li>${icon('check')} ${escapeHTML(item)}</li>`).join('')}</ul>
            </div>
            <div class="suitable-row">
              <span class="suitable-label">适合这样的你</span>
              ${(guide.idealFor || []).map((item) => `<span class="chip chip--outline">${escapeHTML(item)}</span>`).join('')}
            </div>
          </section>

          <section class="detail-section package-section" id="packages">
            <div class="detail-section-head">
              <div><span class="eyebrow">ROUTES & PRICING</span><h2>我能带你怎么玩</h2></div>
              <span class="section-side-note">${icon('wallet')} 无预付 · 确认后再付款</span>
            </div>
            <div class="package-list" data-package-list>
              ${packageOptions(guide, selectedPackage.id)}
            </div>
          </section>

          <section class="detail-section availability-section">
            <div class="detail-section-head">
              <div><span class="eyebrow">GOOD TO KNOW</span><h2>出发前，先知道这些</h2></div>
            </div>
            <div class="notice-grid">
              <article class="notice-card">
                <span class="notice-icon">${icon('pin')}</span>
                <h3>在公开场所碰面</h3>
                <p>默认约在热门地标、地铁站或咖啡馆。具体地点会在确认预约后一起商量。</p>
              </article>
              <article class="notice-card">
                <span class="notice-icon">${icon('calendar')}</span>
                <h3>档期以沟通为准</h3>
                <p>提交预约后，地陪会在 24 小时内确认。若档期不合适，可以免费改期或取消。</p>
              </article>
              <article class="notice-card">
                <span class="notice-icon">${icon('leaf')}</span>
                <h3>不赶场，无购物</h3>
                <p>路线可以随时调整。累了就坐下喝杯东西，旅行不必完成所有“必去”。</p>
              </article>
            </div>
          </section>

          <section class="detail-section reviews-section" id="reviews">
            <div class="detail-section-head">
              <div><span class="eyebrow">TRAVELER STORIES</span><h2>旅人怎么说</h2></div>
              <div class="reviews-summary-inline">
                <strong>${Number(guide.rating).toFixed(1)}</strong>
                <span class="stars">${starRow()}</span>
                <span>${guide.reviewCount || 0} 条评价</span>
              </div>
            </div>
            ${
              guide.reviews?.length
                ? `<div class="review-grid">${guide.reviews
                    .map(
                      (review) => `
                  <article class="review-card">
                    <div class="review-top">
                      ${avatar(review.author, review.avatarTone, 'sm')}
                      <div><strong>${escapeHTML(review.author)}</strong><span>${escapeHTML(review.packageName)}</span></div>
                      <span class="review-date">${formatDateCN(review.date)}</span>
                    </div>
                    <span class="stars stars--sm">${starRow(review.rating)}</span>
                    <p>${escapeHTML(review.content)}</p>
                  </article>`
                    )
                    .join('')}</div>`
                : `<div class="empty-state empty-state--reviews">
                    <span class="empty-icon">${icon('message')}</span>
                    <h3>还没有旅人留下评价</h3>
                    <p>${escapeHTML(guide.name)} 刚刚加入青禾，成为第一个一起散步的人吧。</p>
                  </div>`
            }
          </section>

          <section class="detail-section safety-section">
            <div class="safety-panel">
              <div class="safety-panel-lead">
                <span>${icon('shield')}</span>
                <div><strong>青禾保障</strong><span>让每一次陌生人的见面，都有边界和底气。</span></div>
              </div>
              <div class="safety-panel-points">
                <span>${icon('badge')} 真实身份认证</span>
                <span>${icon('message')} 平台内沟通留痕</span>
                <span>${icon('wallet')} 确认前不收费</span>
                <span>${icon('check-circle')} 不满意可申诉</span>
              </div>
            </div>
          </section>
        </div>

        <aside class="detail-aside">
          ${
            guide.isOwner
              ? `<div class="booking-card owner-booking-card">
                  <span class="eyebrow">YOUR LISTING</span>
                  <h2>这是你发布的服务</h2>
                  <p>旅人可以通过这个页面预约你。你可以在个人中心暂停接单或查看预约。</p>
                  <div class="owner-status">${icon(guide.status === 'published' ? 'check-circle' : 'clock')} ${guide.status === 'published' ? '正在接单' : '已暂停接单'}</div>
                  <a class="btn btn--primary btn--full" href="/account?tab=services">管理我的服务 ${icon('arrow-right')}</a>
                </div>`
              : `<div class="booking-card" data-booking-card>
                  <div class="booking-head">
                    <div><span class="booking-price">${money(selectedPackage.price)}</span><span class="booking-unit">/ ${escapeHTML(selectedPackage.duration)}起</span></div>
                    <span class="booking-rating">${icon('star')} ${Number(guide.rating).toFixed(1)} <small>(${guide.reviewCount || 0})</small></span>
                  </div>
                  <div class="booking-divider"></div>
                  <div class="booking-field">
                    <label for="booking-package">选择套餐</label>
                    <div class="select-wrap">
                      <select id="booking-package" data-booking-package>
                        ${guide.packages.map((pkg) => `<option value="${escapeHTML(pkg.id)}" ${pkg.id === selectedPackage.id ? 'selected' : ''}>${escapeHTML(pkg.name)} · ${escapeHTML(pkg.duration)} · ${money(pkg.price)}</option>`).join('')}
                      </select>
                      ${icon('chevron-down')}
                    </div>
                  </div>
                  <div class="booking-field">
                    <span class="booking-label">选择日期 <small>${icon('calendar')} 可预约日期</small></span>
                    <div class="date-strip" data-date-strip>${dateChips(selectedDate)}</div>
                  </div>
                  <div class="booking-row">
                    <div class="booking-field">
                      <label for="booking-time">开始时间</label>
                      <div class="select-wrap">
                        <select id="booking-time" data-booking-time>
                          ${TIME_SLOTS.map((time) => `<option value="${time}" ${time === '10:00' ? 'selected' : ''}>${time}</option>`).join('')}
                        </select>
                        ${icon('chevron-down')}
                      </div>
                    </div>
                    <div class="booking-field">
                      <span class="booking-label">同行人数</span>
                      <div class="stepper" data-stepper>
                        <button type="button" data-step="-1" aria-label="减少人数">${icon('minus')}</button>
                        <span data-people>1</span>
                        <button type="button" data-step="1" aria-label="增加人数">${icon('plus')}</button>
                      </div>
                    </div>
                  </div>
                  <div class="booking-field">
                    <label for="booking-note">给地陪留言 <small>选填</small></label>
                    <textarea id="booking-note" data-booking-note rows="2" maxlength="240" placeholder="想走的路线、饮食偏好，或需要接站…"></textarea>
                  </div>
                  <div class="price-breakdown">
                    <div><span>套餐费用</span><strong data-package-price>${money(selectedPackage.price)}</strong></div>
                    <div class="extra-fee-row" data-extra-row hidden><span>超出 4 人服务费</span><strong data-extra-fee>¥0</strong></div>
                    <div class="price-total"><span>合计</span><strong data-booking-total>${money(selectedPackage.price)}</strong></div>
                  </div>
                  <button type="button" class="btn btn--primary btn--full btn--lg" data-submit-booking>确认预约 ${icon('arrow-right')}</button>
                  <p class="booking-note">${icon('lock')} 预约后 24 小时内确认，确认前不收取任何费用</p>
                  <div class="booking-trust">
                    <span>${icon('shield')} 平台保障</span>
                    <span>${icon('message')} 先沟通</span>
                    <span>${icon('leaf')} 免费取消</span>
                  </div>
                </div>`
          }
          <div class="aside-note">
            <span>${icon('info')}</span>
            <p>青禾仅提供信息与预约撮合，请勿私下转账。遇到不合适的邀约，请及时取消并向平台反馈。</p>
          </div>
        </aside>
      </div>
    </div>`;
}

export async function renderGuideDetail(root, route) {
  root.innerHTML = `
    <div class="container detail-loading">
      <div class="skeleton skeleton-line skeleton-line--short"></div>
      <div class="skeleton skeleton-title"></div>
      <div class="detail-loading-grid">
        <div class="skeleton skeleton-gallery"></div>
        <div class="skeleton skeleton-booking"></div>
      </div>
    </div>`;

  let guide;
  try {
    const result = await api(`/api/guides/${encodeURIComponent(route.params.id)}`);
    guide = result.guide;
  } catch (error) {
    renderNotFound(root);
    return;
  }

  setPageTitle(`${guide.name} · ${guide.city}地陪`);
  const trip = takeTripDate();
  root.innerHTML = detailShell(guide, trip.date);
  if (trip.rejected) toast('出发日期需要在今天起 180 天内，已改为明天。', 'error');
  initReveals(root);

  const images = (guide.gallery || [guide.cover]).slice(0, 3);
  root.querySelectorAll('[data-lightbox]').forEach((button) => {
    button.addEventListener('click', () => openLightbox(images, Number(button.dataset.lightbox) || 0));
  });

  const shareButton = root.querySelector('[data-share]');
  shareButton?.addEventListener('click', async () => {
    const url = window.location.origin + currentUrl();
    try {
      await navigator.clipboard.writeText(url);
      toast('链接已复制，可以分享给同行的朋友了');
    } catch {
      window.prompt('复制这个链接分享给朋友：', url);
    }
  });

  const favoriteButton = root.querySelector('[data-detail-favorite]');
  favoriteButton?.addEventListener('click', () => {
    const saved = toggleFavorite(guide.id);
    favoriteButton.classList.toggle('is-saved', saved);
    favoriteButton.setAttribute('aria-pressed', String(saved));
    favoriteButton.setAttribute('aria-label', saved ? '取消收藏' : '收藏这位地陪');
    toast(saved ? '已收藏，之后可以在「我的收藏」里找到' : '已取消收藏', saved ? 'success' : 'info');
  });

  if (guide.isOwner) return;

  const bookingCard = root.querySelector('[data-booking-card]');
  if (!bookingCard) return;

  const mobileBar = root.querySelector('.mobile-booking-bar');
  root.querySelector('[data-mobile-scroll]')?.addEventListener('click', () => {
    bookingCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  if (mobileBar && 'IntersectionObserver' in window) {
    const barObserver = new IntersectionObserver(
      ([entry]) => mobileBar.classList.toggle('is-hidden', entry.isIntersecting),
      { threshold: 0.12 }
    );
    barObserver.observe(bookingCard);
  }

  const packageSelect = bookingCard.querySelector('[data-booking-package]');
  const packageList = root.querySelector('[data-package-list]');
  const dateStrip = bookingCard.querySelector('[data-date-strip]');
  const timeSelect = bookingCard.querySelector('[data-booking-time]');
  const noteInput = bookingCard.querySelector('[data-booking-note]');
  const stepper = bookingCard.querySelector('[data-stepper]');
  const peopleEl = bookingCard.querySelector('[data-people]');
  const priceEl = bookingCard.querySelector('[data-package-price]');
  const extraRow = bookingCard.querySelector('[data-extra-row]');
  const extraFeeEl = bookingCard.querySelector('[data-extra-fee]');
  const totalEl = bookingCard.querySelector('[data-booking-total]');
  const submitButton = bookingCard.querySelector('[data-submit-booking]');
  const priceHead = bookingCard.querySelector('.booking-price');
  const unitHead = bookingCard.querySelector('.booking-unit');

  let selectedPackageId = guide.packages.find(pkg => pkg.id === route.search.get('package'))?.id || guide.packages[0].id;
  let selectedDate = trip.date;
  let people = Math.min(8, Math.max(1, Math.round(Number(route.search.get('people')) || 1)));
  if (TIME_SLOTS.includes(route.search.get('time'))) timeSelect.value = route.search.get('time');

  const getPackage = () => guide.packages.find((pkg) => pkg.id === selectedPackageId) || guide.packages[0];

  const updatePrice = () => {
    const pkg = getPackage();
    const extra = Math.max(0, people - 4) * 60;
    const total = pkg.price + extra;
    priceEl.textContent = money(pkg.price);
    totalEl.textContent = money(total);
    extraRow.hidden = extra === 0;
    if (extraFeeEl) extraFeeEl.textContent = money(extra);
    peopleEl.textContent = String(people);
    priceHead.textContent = money(pkg.price);
    unitHead.textContent = `/ ${pkg.duration}起`;
    if (packageSelect.value !== selectedPackageId) packageSelect.value = selectedPackageId;
    if (packageList) {
      packageList.querySelectorAll('[data-package-option]').forEach((option) => {
        const selected = option.dataset.packageOption === selectedPackageId;
        option.classList.toggle('is-selected', selected);
        const input = option.querySelector('input');
        if (input) input.checked = selected;
      });
    }
  };

  const selectDate = (iso, button) => {
    selectedDate = iso;
    dateStrip.querySelectorAll('[data-date]').forEach((chip) => {
      const active = chip.dataset.date === selectedDate;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', String(active));
    });
    if (button) button.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  };

  packageSelect.addEventListener('change', () => {
    selectedPackageId = packageSelect.value;
    updatePrice();
  });

  packageList?.querySelectorAll('[data-package-option] input').forEach((input) => {
    input.addEventListener('change', () => {
      if (!input.checked) return;
      selectedPackageId = input.value;
      updatePrice();
    });
  });

  dateStrip.addEventListener('click', (event) => {
    const button = event.target.closest('[data-date]');
    if (!button || button.disabled) return;
    selectDate(button.dataset.date, button);
  });

  stepper.addEventListener('click', (event) => {
    const button = event.target.closest('[data-step]');
    if (!button) return;
    people = Math.min(8, Math.max(1, people + Number(button.dataset.step)));
    updatePrice();
  });

  updatePrice();
  selectDate(selectedDate);

  submitButton.addEventListener('click', async () => {
    if (!selectedDate) {
      toast('请先选择一个出发日期', 'error');
      return;
    }
    const user = await requireAuth('登录后就能预约这位地陪，行程确认前不收费。');
    if (!user) return;

    const pkg = getPackage();
    submitButton.disabled = true;
    const original = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner"></span><span>正在送出预约…</span>';
    try {
      const { booking } = await api('/api/bookings', {
        method: 'POST',
        body: {
          guideId: guide.id,
          packageId: pkg.id,
          date: selectedDate,
          time: timeSelect.value,
          people,
          note: noteInput.value.trim()
        }
      });
      const modal = showModal(
        `<div class="booking-success">
          <span class="success-icon">${icon('check')}</span>
          <span class="eyebrow">REQUEST SENT</span>
          <h2>预约申请已送出</h2>
          <p>${escapeHTML(guide.name)} 会在 24 小时内确认档期，确认前不会向你收取任何费用。</p>
          <div class="success-detail-card">
            <div class="success-detail-main">
              <img src="${escapeHTML(guide.cover)}" alt="">
              <div><strong>${escapeHTML(guide.name)} · ${escapeHTML(guide.city)}</strong><span>${escapeHTML(pkg.name)} · ${people} 人</span></div>
            </div>
            <div class="success-detail-grid">
              <span>${icon('calendar')} ${formatDateCN(booking.date, { year: true })} ${booking.time}</span>
              <span>${icon('wallet')} 合计 ${money(booking.total)}</span>
              <span>${icon('clock')} 等待地陪确认</span>
            </div>
          </div>
          <button type="button" class="btn btn--primary btn--full" data-go-account>查看我的预约 ${icon('arrow-right')}</button>
          <button type="button" class="btn btn--ghost btn--full" data-go-back>继续看看</button>
          <span class="success-note">${icon('shield')} 可在「我的预约」中随时取消</span>
        </div>`,
        { className: 'modal--success', showClose: true }
      );
      modal.dialog.querySelector('[data-go-account]').addEventListener('click', () => {
        modal.close();
        navigate('/account');
      });
      modal.dialog.querySelector('[data-go-back]').addEventListener('click', () => modal.close());
    } catch (error) {
      toast(error instanceof ApiError ? error.message : '预约没有送出，请稍后再试', 'error');
    } finally {
      submitButton.disabled = false;
      submitButton.innerHTML = original;
    }
  });
}
