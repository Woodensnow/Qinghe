import { api } from '../api.js?v=1.7.0';
import { guideCard, guideCardSkeleton } from '../components/guide-card.js?v=1.7.0';
import { navigate, replaceUrl } from '../router.js?v=1.7.0';
import { appState } from '../state.js?v=1.7.0';
import {
  closeModal,
  debounce,
  escapeHTML,
  formatDateCN,
  icon,
  initReveals,
  isBookableDate,
  readTripDate,
  setPageTitle,
  showModal,
  toast,
  writeTripDate
} from '../ui.js?v=1.7.0';

const PRICE_OPTIONS = [
  { value: '', label: '全部价格' },
  { value: '0-200', label: '¥200 以下' },
  { value: '200-300', label: '¥200 – 300' },
  { value: '300-400', label: '¥300 – 400' },
  { value: '400-9999', label: '¥400 以上' }
];

function getFilters(search) {
  return {
    city: search.get('city') || '',
    service: search.get('service') || '',
    language: search.get('language') || '',
    price: search.get('price') || '',
    q: search.get('q') || '',
    sort: search.get('sort') || 'recommended',
    date: search.get('date') || ''
  };
}

function filterGuides(guides, filters) {
  let result = [...guides];
  if (filters.city) result = result.filter((guide) => guide.city === filters.city);
  if (filters.service) result = result.filter((guide) => guide.services.includes(filters.service));
  if (filters.language) result = result.filter((guide) => guide.languages.includes(filters.language));
  if (filters.q) {
    const q = filters.q.toLowerCase();
    result = result.filter((guide) =>
      [guide.name, guide.city, guide.headline, ...(guide.tags || []), ...(guide.services || [])].join(' ').toLowerCase().includes(q)
    );
  }
  if (filters.price) {
    const [min, max] = filters.price.split('-').map(Number);
    result = result.filter((guide) => guide.price >= min && guide.price <= max);
  }
  const sorters = {
    recommended: (a, b) => Number(b.featured) - Number(a.featured) || b.rating - a.rating || b.orders - a.orders,
    'price-asc': (a, b) => a.price - b.price,
    'price-desc': (a, b) => b.price - a.price,
    rating: (a, b) => b.rating - a.rating || b.reviewCount - a.reviewCount,
    popular: (a, b) => b.orders - a.orders,
    newest: (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
  };
  return result.sort(sorters[filters.sort] || sorters.recommended);
}

export function renderGuides(root, route) {
  const meta = appState.meta;
  const filters = getFilters(route.search);
  const storedDate = readTripDate();
  if (storedDate && !isBookableDate(storedDate)) writeTripDate('');
  const requestedDate = filters.date;
  const plannedDate = isBookableDate(requestedDate) ? requestedDate : '';
  const dateRejected = Boolean(requestedDate) && !plannedDate;
  if (dateRejected) {
    filters.date = '';
    const params = new URLSearchParams(route.search);
    params.delete('date');
    const query = params.toString();
    replaceUrl(`/guides${query ? `?${query}` : ''}`);
  } else if (plannedDate) {
    writeTripDate(plannedDate);
  }
  setPageTitle('找地陪');

  const popularCities = meta?.popularCities || [];
  const cityCounts = new Map();
  let allGuides = [];

  const cityTabsMarkup = () => {
    const cities = filters.city
      ? [filters.city, ...popularCities.filter((city) => city !== filters.city)]
      : popularCities;
    const total = allGuides.length ? allGuides.length : '—';
    return `<button type="button" class="city-tab ${!filters.city ? 'is-active' : ''}" data-city="">全国 <span>${total}</span></button>
      <button type="button" class="city-tab city-tab--more" data-city-more>${icon('map')} 更多城市</button>
      ${cities
        .map(
          (city) =>
            `<button type="button" class="city-tab ${filters.city === city ? 'is-active' : ''}" data-city="${escapeHTML(city)}">${escapeHTML(city)} <span>${allGuides.length ? cityCounts.get(city) || 0 : '—'}</span></button>`
        )
        .join('')}`;
  };

  root.innerHTML = `
    <section class="page-hero page-hero--guides">
      <div class="page-hero-orb" aria-hidden="true"></div>
      <div class="container">
        <nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><span>找地陪</span></nav>
        <div class="guides-hero-grid">
          <div class="guides-hero-copy">
            <span class="eyebrow">LOCAL GUIDE · 地陪</span>
            <h1>找一位懂这座城市的<br><em>本地人</em>。</h1>
            <p>不赶景点，不背攻略。让一个真正生活在这里的人，带你走进街巷、菜场和日常。</p>
            <div class="guides-hero-points">
              <span>${icon('shield')} 本地人认证</span>
              <span>${icon('wallet')} 预约前不收费</span>
              <span>${icon('leaf')} 纯玩无购物</span>
              <span>${icon('pin')} 全国 ${meta?.cityCount || 151} 城</span>
            </div>
          </div>
          <div class="guides-hero-note">
            <span class="guides-note-icon">${icon('quote')}</span>
            <p>“旅行里最难得的，不是拍到多少景点，而是有人告诉你，这条巷子为什么值得拐进去。”</p>
            <span class="guides-note-author">—— 青禾地陪 · 林小满</span>
            <div class="guides-note-stamp">${icon('leaf')} LOCAL<br>FRIEND</div>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--listing">
      <div class="container">
        <div class="filter-panel">
          <div class="city-tabs" data-city-tabs>${cityTabsMarkup()}</div>
          <div class="filter-toolbar">
            <label class="filter-search">
              ${icon('search')}
              <input type="search" placeholder="搜名字、城市、路线或关键词" value="${escapeHTML(filters.q)}" data-filter="q" aria-label="搜索地陪">
            </label>
            <label class="filter-select">
              <span>服务</span>
              <select data-filter="service">
                <option value="">全部服务</option>
                ${(meta?.serviceTypes || []).map((service) => `<option value="${escapeHTML(service)}" ${filters.service === service ? 'selected' : ''}>${escapeHTML(service)}</option>`).join('')}
              </select>
            </label>
            <label class="filter-select">
              <span>语言</span>
              <select data-filter="language">
                <option value="">全部语言</option>
                ${(meta?.languages || []).map((language) => `<option value="${escapeHTML(language)}" ${filters.language === language ? 'selected' : ''}>${escapeHTML(language)}</option>`).join('')}
              </select>
            </label>
            <label class="filter-select">
              <span>价格</span>
              <select data-filter="price">
                ${PRICE_OPTIONS.map((option) => `<option value="${option.value}" ${filters.price === option.value ? 'selected' : ''}>${option.label}</option>`).join('')}
              </select>
            </label>
            <label class="filter-select filter-select--sort">
              <span>排序</span>
              <select data-filter="sort">
                <option value="recommended" ${filters.sort === 'recommended' ? 'selected' : ''}>推荐优先</option>
                <option value="popular" ${filters.sort === 'popular' ? 'selected' : ''}>最多预约</option>
                <option value="rating" ${filters.sort === 'rating' ? 'selected' : ''}>评分最高</option>
                <option value="price-asc" ${filters.sort === 'price-asc' ? 'selected' : ''}>价格从低到高</option>
                <option value="price-desc" ${filters.sort === 'price-desc' ? 'selected' : ''}>价格从高到低</option>
                <option value="newest" ${filters.sort === 'newest' ? 'selected' : ''}>最新入驻</option>
              </select>
            </label>
            <button type="button" class="filter-reset" data-reset>重置</button>
          </div>
          <div class="filter-summary" data-filter-summary hidden></div>
        </div>

        <div class="listing-head">
          <div>
            <h2>为你找到 <span data-result-count>—</span> 位本地搭子</h2>
            <p data-result-sub>正在翻找这座城市的隐藏路线…</p>
          </div>
          ${plannedDate ? `<span class="plan-date">${icon('calendar')} 计划 ${escapeHTML(formatDateCN(plannedDate))} 出发</span>` : ''}
        </div>
        ${dateRejected ? `<p class="plan-date-warning" role="alert">${icon('alert')} 这个出发日期无法使用。请重新选择今天起 180 天内的日期。</p>` : ''}

        <div class="guide-grid" data-guide-results>
          ${guideCardSkeleton()}${guideCardSkeleton()}${guideCardSkeleton()}
        </div>

        <div class="listing-cta">
          <div>
            <span class="eyebrow">ARE YOU A LOCAL?</span>
            <h2>如果你也熟悉自己的城市</h2>
            <p>把常走的路、常去的店，变成别人旅行里最特别的一天。</p>
          </div>
          <a class="btn btn--primary btn--lg" href="/become">发布我的地陪服务 ${icon('arrow-right')}</a>
        </div>
      </div>
    </section>`;

  const resultsEl = root.querySelector('[data-guide-results]');
  const countEl = root.querySelector('[data-result-count]');
  const subEl = root.querySelector('[data-result-sub]');
  const summaryEl = root.querySelector('[data-filter-summary]');
  const resetButton = root.querySelector('[data-reset]');

  const updateUrl = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    replaceUrl(`/guides${params.toString() ? `?${params}` : ''}`);
  };

  const updateSummary = (count) => {
    const chips = [];
    if (filters.city) chips.push({ key: 'city', label: filters.city });
    if (filters.service) chips.push({ key: 'service', label: filters.service });
    if (filters.language) chips.push({ key: 'language', label: filters.language });
    if (filters.price) chips.push({ key: 'price', label: PRICE_OPTIONS.find((item) => item.value === filters.price)?.label || filters.price });
    if (filters.q) chips.push({ key: 'q', label: `“${filters.q}”` });
    summaryEl.hidden = chips.length === 0;
    summaryEl.innerHTML = chips.length
      ? `<span class="summary-label">当前筛选</span>${chips
          .map(
            (chip) =>
              `<button type="button" class="summary-chip" data-remove="${chip.key}">${escapeHTML(chip.label)} ${icon('close')}</button>`
          )
          .join('')}<button type="button" class="summary-clear" data-reset>全部清除</button>`
      : '';
    summaryEl.querySelectorAll('[data-remove]').forEach((button) => {
      button.addEventListener('click', () => {
        filters[button.dataset.remove] = '';
        syncControls();
        applyFilters();
      });
    });
    summaryEl.querySelector('[data-reset]')?.addEventListener('click', resetFilters);
    resetButton.classList.toggle('is-visible', count > 0 && chips.length > 0);
  };

  const syncControls = () => {
    root.querySelectorAll('[data-filter]').forEach((control) => {
      if (control.type !== 'search') control.value = filters[control.dataset.filter] || '';
    });
    const searchInput = root.querySelector('[data-filter="q"]');
    if (searchInput) searchInput.value = filters.q;
  };

  const applyFilters = () => {
    root.querySelector('[data-city-tabs]').innerHTML = cityTabsMarkup();
    const filtered = filterGuides(allGuides, filters);
    countEl.textContent = String(filtered.length);
    subEl.textContent = filtered.length
      ? `从 ${allGuides.length} 位认证地陪里，挑出最合你节奏的那一位。`
      : '换一个城市或筛选项，也许会有惊喜。';
    resultsEl.innerHTML = filtered.length
      ? filtered.map(guideCard).join('')
      : `<div class="empty-state empty-state--wide">
          <span class="empty-icon">${icon('compass')}</span>
          <h3>这片街区暂时没有合适的搭子</h3>
          <p>试试放宽价格或语言筛选，或者换一座城市看看。</p>
          <button type="button" class="btn btn--primary" data-reset>清除筛选</button>
        </div>`;
    resultsEl.querySelectorAll('[data-reset]').forEach((button) => button.addEventListener('click', resetFilters));
    updateSummary(filtered.length);
    updateUrl();
    initReveals(resultsEl);
  };

  const resetFilters = () => {
    Object.assign(filters, { city: '', service: '', language: '', price: '', q: '', sort: 'recommended' });
    syncControls();
    applyFilters();
    toast('筛选已重置', 'info');
  };

  root.querySelector('[data-city-tabs]').addEventListener('click', (event) => {
    const more = event.target.closest('[data-city-more]');
    if (more) {
      openCityPicker();
      return;
    }
    const button = event.target.closest('[data-city]');
    if (!button) return;
    filters.city = button.dataset.city;
    applyFilters();
  });

  root.querySelectorAll('[data-filter]').forEach((control) => {
    if (control.type === 'search') {
      const onSearch = debounce(() => {
        filters.q = control.value.trim();
        applyFilters();
      }, 220);
      control.addEventListener('input', onSearch);
    } else {
      control.addEventListener('change', () => {
        filters[control.dataset.filter] = control.value;
        applyFilters();
      });
    }
  });
  resetButton.addEventListener('click', resetFilters);

  api('/api/guides')
    .then(({ guides }) => {
      allGuides = guides;
      guides.forEach((guide) => {
        cityCounts.set(guide.city, (cityCounts.get(guide.city) || 0) + 1);
      });
      applyFilters();
    })
    .catch(() => {
      resultsEl.innerHTML = `<div class="inline-error inline-error--wide">${icon('alert')} 本地搭子们暂时走开了一下，<button class="text-link" type="button" data-retry>重新加载</button></div>`;
      resultsEl.querySelector('[data-retry]')?.addEventListener('click', () => renderGuides(root, route));
      subEl.textContent = '加载失败，请稍后再试。';
    });

  function openCityPicker() {
    const baseList = () => {
      const total = allGuides.length;
      const groups = (meta?.cityGroups || [])
        .map((group) => {
          const cities = group.cities
            .map(
              (city) => `<button type="button" class="city-pick-item ${filters.city === city ? 'is-active' : ''}" data-pick-city="${escapeHTML(city)}">
                <span>${escapeHTML(city)}</span><small>${cityCounts.get(city) || 0} 位</small>
              </button>`
            )
            .join('');
          return `<section class="city-picker-group"><h3>${escapeHTML(group.region)}</h3><div class="city-picker-grid">${cities}</div></section>`;
        })
        .join('');
      return `<button type="button" class="city-pick-nation ${!filters.city ? 'is-active' : ''}" data-pick-city="">
        <span>${icon('pin')} 全国</span><small>${total} 位本地搭子</small>
      </button>${groups}`;
    };

    const modal = showModal(
      `<div class="city-picker-modal">
        <span class="eyebrow">CITIES ACROSS CHINA</span>
        <h2>选一座城市，看看谁在等你</h2>
        <p>覆盖 ${meta?.regionCount || 34} 个省级行政区、${meta?.cityCount || 151} 座城市。没有地陪的城市，也欢迎你成为第一个。</p>
        <label class="city-picker-search">
          ${icon('search')}
          <input type="search" placeholder="搜索城市，例如：大理、哈尔滨、台北" data-city-picker-search autofocus>
        </label>
        <div class="city-picker-list" data-city-picker-list>${baseList()}</div>
        <div class="city-picker-foot">
          <span>${icon('leaf')} 每座城市都值得被慢慢认识</span>
          <a class="btn btn--ghost btn--sm" href="/become">成为第一个本地搭子 ${icon('arrow-right')}</a>
        </div>
      </div>`,
      { className: 'modal--city-picker' }
    );

    const list = modal.dialog.querySelector('[data-city-picker-list]');
    const search = modal.dialog.querySelector('[data-city-picker-search]');
    const updateList = () => {
      const query = search.value.trim();
      if (!query) {
        list.innerHTML = baseList();
        return;
      }
      const groups = (meta?.cityGroups || [])
        .map((group) => {
          const cities = group.cities.filter((city) => city.includes(query));
          if (!cities.length) return '';
          return `<section class="city-picker-group"><h3>${escapeHTML(group.region)}</h3><div class="city-picker-grid">${cities
            .map(
              (city) => `<button type="button" class="city-pick-item ${filters.city === city ? 'is-active' : ''}" data-pick-city="${escapeHTML(city)}">
                <span>${escapeHTML(city)}</span><small>${cityCounts.get(city) || 0} 位</small>
              </button>`
            )
            .join('')}</div></section>`;
        })
        .join('');
      list.innerHTML = groups || `<div class="city-picker-empty">${icon('compass')} 暂时没有找到「${escapeHTML(query)}」，试试另一个名字。</div>`;
    };
    search.addEventListener('input', updateList);
    list.addEventListener('click', (event) => {
      const button = event.target.closest('[data-pick-city]');
      if (!button) return;
      filters.city = button.dataset.pickCity;
      closeModal();
      applyFilters();
    });
  }

  initReveals(root);
}
