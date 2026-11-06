import { api } from '../api.js?v=1.7.0';
import { session } from '../session.js?v=1.7.0';
import { openAuthModal } from '../components/auth-modal.js?v=1.7.0';
import { appState } from '../state.js?v=1.7.0';
import { navigate } from '../router.js?v=1.7.0';
import { escapeHTML as e, cityOptionsHTML, localDateISO, maxTripDateISO, setPageTitle, toast } from '../ui.js?v=1.7.0';

const checks = (name, values, chosen = []) => `<div class="match-checks">${values.map(v => `<label><input type="checkbox" name="${name}" value="${e(v)}" ${chosen.includes(v) ? 'checked' : ''}> ${e(v)}</label>`).join('')}</div>`;
const field = (label, content) => `<label class="field"><span class="field-label">${label}</span>${content}</label>`;
const picks = (form, name) => [...form.querySelectorAll(`[name="${name}"]:checked`)].map(input => input.value);
const bookingLink = (match, trip) => `/guides/${encodeURIComponent(match.guideId)}?${new URLSearchParams({ package: match.offer.packageId, date: trip.date, time: trip.time, people: trip.people })}`;

export async function renderMatching(root) {
  setPageTitle('双边匹配');
  if (!session.user) {
    root.innerHTML = `<section class="container section"><h1>找到双方都合适的搭子</h1><p>填写行程，也了解地陪的接单偏好。</p><button class="btn btn--primary" data-match-login>登录并开始</button></section>`;
    root.querySelector('[data-match-login]').onclick = async () => {
      if (await openAuthModal({ mode: 'login' })) renderMatching(root);
    };
    return;
  }
  root.innerHTML = `<section class="container section"><p>正在读取行程和接单偏好…</p></section>`;
  try {
    const [meta, { trip }, { guides }] = await Promise.all([
      api('/api/matching/meta'), api('/api/matching/trip'), api('/api/guides/mine')
    ]);
    if (!root.isConnected || document.body.dataset.page !== 'matching') return;
    const catalog = appState.meta;
    const t = trip || {};
    let activeTrip = trip;
    root.innerHTML = `<section class="container section matching-page">
      <span class="eyebrow">FIND YOUR LOCAL CONNECTION</span>
      <h1>你的期待，也遇见对方的期待。</h1>
      <p>城市、预算和档期先合适，再比较旅行兴趣、节奏和双方的文字介绍。</p>
      <p class="match-notice">这是合成样例训练的课程演示。推荐分表示模型排序，不是接受概率。${!meta.hasTorch || !meta.hasModel ? '当前模型尚未就绪，请按 README 完成安装与训练。' : ''}</p>
      <div class="match-tabs"><button class="btn btn--primary" data-mode="traveler">我是旅人</button><button class="btn btn--ghost" data-mode="guide">我是地陪</button></div>
      <div data-traveler-panel>
        <form class="match-form" data-trip-form>
          <h2>这次想怎么玩？</h2>
          <div class="form-grid form-grid--two">
            ${field('目的地', `<select name="city" required>${cityOptionsHTML(catalog.cityGroups, t.city || '', { allLabel: '选择城市' })}</select>`)}
            ${field('日期', `<input name="date" type="date" min="${localDateISO()}" max="${maxTripDateISO()}" value="${e(t.date || localDateISO())}" required>`)}
            ${field('开始时间', `<select name="time">${['09:00','10:00','11:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00'].map(v => `<option ${v === (t.time || '10:00') ? 'selected' : ''}>${v}</option>`).join('')}</select>`)}
            ${field('套餐时长', `<select name="hours">${[3,4,8].map(v => `<option value="${v}" ${v === (t.hours || 4) ? 'selected' : ''}>${v} 小时</option>`).join('')}</select>`)}
            ${field('同行人数', `<input name="people" type="number" min="1" max="8" value="${t.people || 2}" required>`)}
            ${field('整团总预算（含超员费用）', `<input name="budget" type="number" min="1" value="${t.budget || 500}" required>`)}
          </div>
          <fieldset><legend>需要的服务（地陪须全部提供）</legend>${checks('services', catalog.serviceTypes, t.services || ['城市漫步'])}</fieldset>
          <fieldset><legend>可沟通语言（至少共同掌握一种）</legend>${checks('languages', catalog.languages, t.languages || ['中文'])}</fieldset>
          <fieldset><legend>旅行兴趣</legend>${checks('interests', meta.interests, t.interests || ['咖啡'])}</fieldset>
          <fieldset><legend>喜欢的节奏</legend>${checks('paces', meta.paces, t.paces || ['慢慢逛'])}</fieldset>
          ${field('用自己的话说说期待', `<textarea name="description" maxlength="300" rows="3" placeholder="例如：喜欢咖啡和老街，想多听一点本地人的故事。">${e(t.description || '')}</textarea>`)}
          <label class="match-consent"><input type="checkbox" name="share" required ${trip ? 'checked' : ''}> 同意向符合条件的地陪展示昵称、行程和偏好，以便双方联系；不展示邮箱。</label>
          <div class="match-actions"><button class="btn btn--primary" type="submit">保存需求并匹配</button><button class="btn btn--ghost" type="button" data-close-trip>停止展示本次需求</button></div>
        </form>
      </div>
      <div data-guide-panel hidden>
        ${guides.length ? `<form class="match-form" data-provider-form>
          <h2>你喜欢接待什么样的行程？</h2>
          ${field('选择我的服务', `<select name="guideId">${guides.map(g => `<option value="${e(g.id)}">${e(g.name)} · ${e(g.city)}${g.status === 'paused' ? '（已暂停，恢复后参与匹配）' : ''}</option>`).join('')}</select>`)}
          <div data-provider-fields></div>
          <button class="btn btn--primary" type="submit">保存偏好并查看旅人</button>
        </form>` : `<div class="match-form"><h2>先发布一条地陪服务</h2><p>有了服务与接单偏好，才能为你推荐合适的旅人。</p><a class="btn btn--primary" href="/become">发布服务</a></div>`}
      </div>
      <div class="match-results" data-matches aria-live="polite"></div>
    </section>`;
    const results = root.querySelector('[data-matches]');
    let mode = 'traveler';
    const showResults = async (side, guideId = '') => {
      results.innerHTML = '<p>正在比较双方偏好…</p>';
      try {
        const data = await api(`/api/matching/${side === 'traveler' ? 'guides' : `travelers?guideId=${encodeURIComponent(guideId)}`}`);
        if (!root.isConnected || mode !== side) return;
        results.innerHTML = `<h2>${data.matches.length ? '双方都值得了解的选择' : '暂时没有双方信息完整且符合条件的组合'}</h2>
          <p>推荐分参考双方偏好，见面前请继续沟通确认。</p>
          ${data.matches.map(m => `<article class="match-result">
            <div><span class="eyebrow">${e(side === 'traveler' ? m.guide.city : m.trip.city)}</span><h3>${e(side === 'traveler' ? m.guide.name : m.traveler.name)}</h3>
            <p>${e(side === 'traveler' ? m.guide.headline : `${m.trip.date} ${m.trip.time} · ${m.trip.people} 人 · ${m.trip.description}`)}</p>
            <p>${e(m.offer.packageName)} · 整团 ¥${m.offer.total}</p>
            <ul>${m.reasons.map(r => `<li>${e(r)}</li>`).join('')}</ul></div>
            <div class="match-score"><strong>${m.score}</strong><span>双边推荐分</span><small>旅人视角 ${m.travelerScore} · 地陪视角 ${m.guideScore}</small>
            ${side === 'traveler' ? `<a class="btn btn--primary btn--sm" href="${e(bookingLink(m, activeTrip))}">查看服务并预约</a><button class="btn btn--ghost btn--sm" data-chat-guide="${e(m.guideId)}">先聊聊</button>` : `<button class="btn btn--primary btn--sm" data-contact-trip="${e(m.tripId)}" data-contact-guide="${e(m.guideId)}">联系旅人</button>`}</div>
          </article>`).join('')}
          ${Object.keys(data.excluded).length ? `<details class="match-notice"><summary>哪些条件减少了候选？</summary><ul>${Object.entries(data.excluded).map(([reason, count]) => `<li>${e(reason)}：${count} 个组合</li>`).join('')}</ul></details>` : ''}`;
        results.querySelectorAll('[data-contact-trip]').forEach(button => button.onclick = async () => {
          button.disabled = true;
          try {
            const { conversationId } = await api('/api/matching/contact', { method: 'POST', body: { tripId: button.dataset.contactTrip, guideId: button.dataset.contactGuide } });
            navigate(`/messages?conversation=${encodeURIComponent(conversationId)}`);
          } catch (error) { toast(error.message, 'error'); button.disabled = false; }
        });
      } catch (error) { results.innerHTML = `<p class="match-notice">${e(error.message)}</p>`; }
    };
    root.querySelectorAll('[data-mode]').forEach(button => button.onclick = () => {
      mode = button.dataset.mode;
      root.querySelector('[data-traveler-panel]').hidden = mode !== 'traveler';
      root.querySelector('[data-guide-panel]').hidden = mode !== 'guide';
      root.querySelectorAll('[data-mode]').forEach(b => { b.classList.toggle('btn--primary', b === button); b.classList.toggle('btn--ghost', b !== button); });
      results.innerHTML = '';
    });
    root.querySelector('[data-trip-form]').onsubmit = async event => {
      event.preventDefault();
      const form = event.currentTarget;
      const button = form.querySelector('[type="submit"]');
      button.disabled = true;
      const values = Object.fromEntries(new FormData(form));
      try {
        const saved = await api('/api/matching/trip', { method: 'POST', body: { ...values,
          people: Number(values.people), budget: Number(values.budget), hours: Number(values.hours), share: form.elements.share.checked,
          ...Object.fromEntries(['services','languages','interests','paces'].map(k => [k, picks(form, k)])) } });
        activeTrip = saved.trip;
        await showResults('traveler');
      } catch (error) { toast(error.message, 'error'); }
      finally { button.disabled = false; }
    };
    root.querySelector('[data-close-trip]').onclick = async () => {
      try { await api('/api/matching/trip', { method: 'DELETE' }); results.innerHTML = '<p>需求已停止展示；已有预约和聊天不受影响。</p>'; root.querySelector('[name="share"]').checked = false; }
      catch (error) { toast(error.message, 'error'); }
    };
    const providerForm = root.querySelector('[data-provider-form]');
    if (providerForm) {
      const loadPreferences = () => {
        const g = guides.find(g => g.id === providerForm.elements.guideId.value);
        const p = g.matchPreferences || {};
        providerForm.querySelector('[data-provider-fields]').innerHTML = `
          ${field('最多接待人数', `<input name="maxPeople" type="number" min="1" max="8" value="${p.maxPeople || 4}" required>`)}
          <fieldset><legend>愿意接单的星期</legend>${checks('weekdays', ['周一','周二','周三','周四','周五','周六','周日'], (p.weekdays || [0,1,2,3,4,5,6]).map(i => ['周一','周二','周三','周四','周五','周六','周日'][i]))}</fieldset>
          <fieldset><legend>喜欢接待的旅行兴趣</legend>${checks('interests', meta.interests, p.interests || ['咖啡'])}</fieldset>
          <fieldset><legend>喜欢的行程节奏</legend>${checks('paces', meta.paces, p.paces || ['慢慢逛'])}</fieldset>
          ${field('休息日期（逗号分隔）', `<input name="blockedDates" value="${e((p.blockedDates || []).join(', '))}" placeholder="例如 2026-12-01, 2026-12-02">`)}
          ${field('描述你喜欢接待的行程', `<textarea name="text" rows="3" maxlength="300">${e(p.text || '')}</textarea>`)}
          <p>服务类型和语言沿用发布信息；保存后参与双边匹配。</p>`;
      };
      providerForm.elements.guideId.onchange = loadPreferences;
      loadPreferences();
      providerForm.onsubmit = async event => {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(providerForm));
        const button = providerForm.querySelector('[type="submit"]');
        button.disabled = true;
        try {
          const { guide } = await api(`/api/matching/preferences/${encodeURIComponent(values.guideId)}`, { method: 'PATCH', body: {
            maxPeople: Number(values.maxPeople), interests: picks(providerForm, 'interests'), paces: picks(providerForm, 'paces'),
            weekdays: picks(providerForm, 'weekdays').map(day => ['周一','周二','周三','周四','周五','周六','周日'].indexOf(day)),
            blockedDates: values.blockedDates.split(/[,，\s]+/).filter(Boolean), text: values.text } });
          guides[guides.findIndex(g => g.id === guide.id)] = guide;
          await showResults('guide', guide.id);
        } catch (error) { toast(error.message, 'error'); }
        finally { button.disabled = false; }
      };
    }
    if (trip) await showResults('traveler');
  } catch (error) { root.innerHTML = `<section class="container section"><p>${e(error.message)}</p></section>`; }
}
