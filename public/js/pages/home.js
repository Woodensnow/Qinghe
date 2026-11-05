import { api } from '../api.js?v=1.7.0';
import { guideCard, guideCardSkeleton } from '../components/guide-card.js?v=1.7.0';
import { navigate } from '../router.js?v=1.7.0';
import { appState } from '../state.js?v=1.7.0';
import {
  addDays,
  avatar,
  cityOptionsHTML,
  escapeHTML,
  icon,
  initReveals,
  localDateISO,
  setPageTitle,
  toast
} from '../ui.js?v=1.7.0';

function trackCards(meta) {
  return `
    <button class="track-card track-card--main reveal" type="button" data-track="guide">
      <img src="/assets/images/guide-hangzhou.jpg" alt="" loading="lazy">
      <span class="track-main-shade" aria-hidden="true"></span>
      <span class="track-main-top">
        <span class="pill pill--glass">${icon('sparkles')} 主推板块</span>
        <span class="track-arrow">${icon('arrow-up-right')}</span>
      </span>
      <span class="track-main-content">
        <span class="track-kicker">LOCAL GUIDE · 地陪</span>
        <strong>找位本地人<br>陪你慢慢逛</strong>
        <span class="track-main-meta">${icon('pin')} 全国 ${meta.cityCount || 151} 城 · ${meta.stats?.guides || 6} 位精选地陪</span>
      </span>
    </button>
    ${(meta.otherTracks || [])
      .map(
        (track) => `
      <button class="track-card track-card--small reveal" type="button" data-coming-soon="${escapeHTML(track.name)}">
        <span class="track-icon">${icon(track.icon)}</span>
        <span class="track-small-content">
          <strong>${escapeHTML(track.name)}</strong>
          <span>${escapeHTML(track.tagline)}</span>
        </span>
        <span class="track-status">即将开放</span>
      </button>`
      )
      .join('')}`;
}

function guideMiniCard() {
  return `
    <div class="hero-guide-card">
      <div class="hero-guide-head">
        ${avatar('林小满', 'sage', 'md')}
        <div>
          <strong>林小满 <span class="verified-dot" title="本地人认证">${icon('check')}</span></strong>
          <span>上海 · 梧桐区城市漫步</span>
        </div>
        <span class="hero-guide-rating">${icon('star')} 4.9</span>
      </div>
      <div class="hero-guide-tags">
        <span>咖啡地图</span><span>会拍照</span><span>不赶路</span>
      </div>
      <div class="hero-guide-foot">
        <span>半日路线</span>
        <strong>¥268 <small>起</small></strong>
      </div>
    </div>`;
}

export function renderHome(root) {
  const meta = appState.meta;
  const stats = meta?.stats || { guides: 6, cities: 6 };
  setPageTitle('');

  root.innerHTML = `
    <section class="home-hero">
      <div class="hero-glow hero-glow--one" aria-hidden="true"></div>
      <div class="hero-glow hero-glow--two" aria-hidden="true"></div>
      <div class="container hero-grid">
        <div class="hero-copy">
          <div class="hero-eyebrow reveal">
            <span class="eyebrow-dot"></span>
            <span>城市轻兼职 · 让闲暇长出新的可能</span>
          </div>
          <h1 class="hero-title reveal">找位本地人，<br>陪你<span class="marker">慢慢逛<svg viewBox="0 0 180 18" preserveAspectRatio="none" aria-hidden="true"><path d="M3 12C50 4 120 3 177 9" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></span>。</h1>
          <p class="hero-sub reveal">不赶景点，不做攻略。把半天交给一个懂城市的人，像朋友一样，走进本地人的日常。<span class="hero-sub-second">也欢迎把熟悉的城市，变成一份时间自由的副业。</span></p>
          <div class="hero-actions reveal">
            <a class="btn btn--primary btn--lg" href="/guides">寻找地陪 ${icon('arrow-right')}</a>
            <a class="btn btn--text btn--lg" href="/become">我想接单 ${icon('arrow-up-right')}</a>
          </div>
          <div class="hero-trust reveal">
            <span>${icon('shield')} 真实身份认证</span>
            <span>${icon('wallet')} 预约前不收费</span>
            <span>${icon('leaf')} 无购物纯玩</span>
          </div>
          <div class="hero-stats reveal">
            <div><strong>全国</strong><span>城市可约</span></div>
            <i></i>
            <div><strong>${stats.guides}</strong><span>位本地搭子</span></div>
            <i></i>
            <div><strong>4.9</strong><span>平均评分</span></div>
          </div>
        </div>

        <div class="hero-visual reveal">
          <div class="hero-photo-frame">
            <img src="/assets/images/hero-shanghai.jpg" alt="上海城市夜景" fetchpriority="high">
            <span class="hero-photo-overlay" aria-hidden="true"></span>
            <div class="hero-photo-label">
              <span class="hero-photo-pin">${icon('pin')}</span>
              <span><small>正在发生</small>上海 · 外滩</span>
            </div>
            <div class="hero-note-card">
              <span class="hero-note-icon">${icon('route')}</span>
              <div>
                <strong>今日路线</strong>
                <span>武康路 → 安福路 → 五原路</span>
              </div>
            </div>
          </div>
          ${guideMiniCard()}
          <div class="hero-availability">
            <span class="availability-pulse"></span>
            <span><strong>明日可约</strong> · 还剩 2 个时段</span>
          </div>
          <div class="hero-sticker" aria-hidden="true">
            <span>LOCAL</span>
            <span>ONLY</span>
            <i>${icon('leaf')}</i>
          </div>
        </div>
      </div>

      <div class="container hero-search-wrap">
        <form class="hero-search" data-search-form>
          <div class="search-intro">
            <span class="search-icon">${icon('compass')}</span>
            <div><strong>规划一次城市散步</strong><span>从选一座城市开始</span></div>
          </div>
          <label class="search-field">
            <span>${icon('pin')} 目的地</span>
            <select name="city">
              ${cityOptionsHTML(meta?.cityGroups, '', { allLabel: '全部城市' })}
            </select>
          </label>
          <label class="search-field">
            <span>${icon('calendar')} 出发日期</span>
            <input type="date" name="date" min="${localDateISO()}" value="${localDateISO(addDays(1))}">
          </label>
          <label class="search-field">
            <span>${icon('walk')} 服务类型</span>
            <select name="type">
              <option value="地陪">地陪 · 城市漫步</option>
              <option disabled>摄影 · 即将开放</option>
              <option disabled>模特 · 即将开放</option>
              <option disabled>博物馆讲解员 · 即将开放</option>
              <option disabled>NPC · 即将开放</option>
            </select>
          </label>
          <button class="btn btn--primary search-submit" type="submit">${icon('search')} 寻找搭子</button>
        </form>
      </div>
    </section>

    <section class="section section--tracks" id="categories">
      <div class="container">
        <div class="section-heading section-heading--split">
          <div>
            <span class="eyebrow">MORE THAN A SIDE GIG</span>
            <h2>不止一种空闲时间的<br>打开方式</h2>
          </div>
          <p>先认真把「地陪」做好。摄影、模特、讲解和 NPC，也正在慢慢长出来。</p>
        </div>
        <div class="track-grid">
          ${trackCards(meta || {})}
        </div>
      </div>
    </section>

    <section class="section section--guides">
      <div class="container">
        <div class="section-heading section-heading--split">
          <div>
            <span class="eyebrow">MEET YOUR LOCAL</span>
            <h2>这座城，他们比你更熟</h2>
          </div>
          <a class="btn btn--ghost" href="/guides">查看全部地陪 ${icon('arrow-right')}</a>
        </div>
        <div class="guide-grid" data-featured-grid>
          ${guideCardSkeleton()}${guideCardSkeleton()}${guideCardSkeleton()}
        </div>
      </div>
    </section>

    <section class="section section--cities">
      <div class="container">
        <div class="city-strip">
          <div class="city-strip-copy">
            <span class="eyebrow">CITY BY CITY</span>
            <h3>从一座熟悉的城市开始</h3>
            <small class="city-strip-note">覆盖 ${meta?.regionCount || 34} 个省级行政区 · ${meta?.cityCount || 151} 座城市</small>
          </div>
          <div class="city-chips">
            ${(meta?.popularCities || []).map((city, index) => `<button type="button" class="city-chip" data-city="${escapeHTML(city)}"><span>${String(index + 1).padStart(2, '0')}</span>${escapeHTML(city)} ${icon('arrow-up-right')}</button>`).join('')}
            <button type="button" class="city-chip city-chip--all" data-all-cities>全国城市 ${icon('arrow-right')}</button>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--how" id="how">
      <div class="container">
        <div class="section-heading section-heading--center">
          <span class="eyebrow">HOW IT WORKS</span>
          <h2>把一次见面，安排得刚刚好</h2>
          <p>不复杂的流程，把时间留给真正的相遇。</p>
        </div>
        <div class="steps-grid">
          <article class="step-card reveal">
            <span class="step-number">01</span>
            <span class="step-icon">${icon('compass')}</span>
            <h3>说说你的计划</h3>
            <p>选好城市、日期和喜欢的节奏。第一次来也没关系，本地搭子会帮你把路线理顺。</p>
            <span class="step-tag">1 分钟</span>
          </article>
          <article class="step-card reveal">
            <span class="step-number">02</span>
            <span class="step-icon">${icon('message')}</span>
            <h3>认识你的本地搭子</h3>
            <p>看看真实评价和擅长路线，提交预约后先沟通需求，确认合适再出发。</p>
            <span class="step-tag">提前 1–3 天</span>
          </article>
          <article class="step-card reveal">
            <span class="step-number">03</span>
            <span class="step-icon">${icon('walk')}</span>
            <h3>见面，慢慢逛</h3>
            <p>约在公开场所碰面，走进街巷、市场和日常。全程无购物，不赶场。</p>
            <span class="step-tag">把时间交给城市</span>
          </article>
        </div>
      </div>
    </section>

    <section class="section section--quote">
      <div class="container quote-layout">
        <div class="quote-card reveal">
          <div class="quote-mark">${icon('quote')}</div>
          <blockquote>小满带我们钻了好几条地图上找不到的小弄堂，还在一个老爷爷开的裁缝铺门口聊了半小时。照片也拍得特别自然，不是那种打卡游客照。</blockquote>
          <div class="quote-author">
            ${avatar('Momo', 'clay', 'sm')}
            <div><strong>Momo</strong><span>上海 · 半日城市漫步</span></div>
            <span class="quote-stars">${icon('star')}${icon('star')}${icon('star')}${icon('star')}${icon('star')}</span>
          </div>
        </div>
        <div class="quote-side reveal">
          <span class="eyebrow">REAL MOMENTS</span>
          <h2>好的陪伴，<br>是旅行里最轻的部分。</h2>
          <p>没有喇叭、没有购物店、没有赶不完的打卡点。只有一个熟悉这里的人，和你一起把时间走慢。</p>
          <div class="quote-side-stats">
            <div><strong>98%</strong><span>预约确认率</span></div>
            <div><strong>4.9</strong><span>平均旅人评分</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--host">
      <div class="container">
        <div class="host-cta reveal">
          <div class="host-cta-image" aria-hidden="true">
            <img src="/assets/images/guide-hangzhou.jpg" alt="" loading="lazy">
          </div>
          <div class="host-cta-content">
            <span class="eyebrow eyebrow--light">BECOME A LOCAL HOST</span>
            <h2>把你的城市，<br>讲给旅人听。</h2>
            <p>熟悉的小路、常去的馆子、知道什么时候光线最好——这些都可以成为你的兼职。时间自己定，服务自己选，青禾帮你被看见。</p>
            <div class="host-perks">
              <span>${icon('clock')} 时间自由</span>
              <span>${icon('wallet')} 半日 ¥200 起</span>
              <span>${icon('shield')} 平台保障</span>
            </div>
            <a class="btn btn--light btn--lg" href="/become">成为地陪 ${icon('arrow-right')}</a>
            <span class="host-note">已有 ${stats.guides} 位本地人加入 · 审核后即可上架</span>
          </div>
          <div class="host-float-card">
            <span class="host-float-icon">${icon('leaf')}</span>
            <div><span>本月新增收入</span><strong>¥ 3,680</strong></div>
            <span class="host-float-up">+28%</span>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--safety">
      <div class="container safety-strip">
        <div class="safety-lead">
          <span class="safety-mark">${icon('shield')}</span>
          <div><strong>每一次相遇，都值得被认真对待</strong><span>真实认证 · 行程留痕 · 平台协助 · 拒绝私下交易</span></div>
        </div>
        <div class="safety-points">
          <span>${icon('badge')} 身份认证</span>
          <span>${icon('message')} 行前沟通</span>
          <span>${icon('check-circle')} 无购物承诺</span>
        </div>
      </div>
    </section>`;

  const form = root.querySelector('[data-search-form]');
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const city = form.elements.city.value;
    const date = form.elements.date.value;
    const params = new URLSearchParams();
    if (city) params.set('city', city);
    if (date) {
      params.set('date', date);
      try {
        sessionStorage.setItem('qinghe_trip_date', date);
      } catch {
        /* noop */
      }
    }
    navigate(`/guides${params.toString() ? `?${params}` : ''}`);
  });

  root.querySelector('[data-track="guide"]').addEventListener('click', () => navigate('/guides'));
  root.querySelectorAll('[data-city]').forEach((button) => {
    button.addEventListener('click', () => navigate(`/guides?city=${encodeURIComponent(button.dataset.city)}`));
  });
  root.querySelector('[data-all-cities]')?.addEventListener('click', () => navigate('/guides'));

  const featured = root.querySelector('[data-featured-grid]');
  api('/api/guides?sort=recommended')
    .then(({ guides }) => {
      appState.homeGuides = guides;
      featured.innerHTML = guides.slice(0, 3).map(guideCard).join('');
      initReveals(featured);
    })
    .catch(() => {
      featured.innerHTML = `<div class="inline-error">${icon('alert')} 暂时没能请出本地搭子，<button type="button" class="text-link" data-retry>再试一次</button></div>`;
      featured.querySelector('[data-retry]')?.addEventListener('click', () => {
        toast('正在重新加载…', 'info');
        renderHome(root);
      });
    });

  initReveals(root);
}
