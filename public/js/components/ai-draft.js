import { api } from '../api.js?v=1.7.0';
import {
  DRAFT_PACKAGES,
  charLength,
  draftFailureMessage,
  engineNote,
  notesProblem,
  validateItineraries
} from '../itinerary.js?v=1.8.0';
import { itineraryList } from './itinerary-timeline.js?v=1.8.0';
import { closeModal, escapeHTML, icon, showModal, toast } from '../ui.js?v=1.7.0';

function clipNotes(value) {
  return Array.from(String(value || '').trim()).slice(0, 300).join('');
}

function nodeRow(node = {}) {
  const row = document.createElement('div');
  row.className = 'itinerary-node';
  row.innerHTML = `
    <input data-node-time maxlength="5" inputmode="numeric" placeholder="14:00" aria-label="时间" autocomplete="off">
    <input data-node-place maxlength="20" placeholder="地点" aria-label="地点" autocomplete="off">
    <input data-node-activity maxlength="80" placeholder="做什么" aria-label="活动" autocomplete="off">
    <button type="button" data-remove-node aria-label="删除这个节点">${icon('minus')}</button>`;
  row.querySelector('[data-node-time]').value = node.time || '';
  row.querySelector('[data-node-place]').value = node.place || '';
  row.querySelector('[data-node-activity]').value = node.activity || '';
  return row;
}

function nodeRowHTML() {
  return `<div class="itinerary-node">
    <input data-node-time maxlength="5" inputmode="numeric" placeholder="14:00" aria-label="时间" autocomplete="off">
    <input data-node-place maxlength="20" placeholder="地点" aria-label="地点" autocomplete="off">
    <input data-node-activity maxlength="80" placeholder="做什么" aria-label="活动" autocomplete="off">
    <button type="button" data-remove-node aria-label="删除这个节点">${icon('minus')}</button>
  </div>`;
}

export function draftEditorHTML() {
  const highlights = [0, 1, 2]
    .map(
      (index) => `<label class="draft-highlight">
        <span>${index + 1}</span>
        <input data-highlight-index="${index}" maxlength="20" placeholder="一句话亮点，最多 20 字" aria-label="亮点 ${index + 1}" autocomplete="off">
      </label>`
    )
    .join('');
  const packages = DRAFT_PACKAGES.map(
    (pkg) => `<section class="draft-package">
      <div class="draft-package-head">
        <strong>${escapeHTML(pkg.name)}</strong>
        <span>${escapeHTML(pkg.duration)}</span>
        <button type="button" class="text-link" data-add-node="${pkg.key}">加一个节点</button>
      </div>
      <div data-node-list="${pkg.key}">${[0, 1, 2].map(() => nodeRowHTML()).join('')}</div>
    </section>`
  ).join('');
  return `<details class="draft-editor" data-draft-editor>
    <summary>
      <strong>亮点和行程</strong>
      <span>三个套餐都要有时间线，可以用「AI 帮我写」</span>
    </summary>
    <div class="draft-editor-body">
      <span class="field-label">三个亮点</span>
      <div class="draft-highlights" data-draft-highlights>${highlights}</div>
      <span class="field-error" data-error-for="highlights"></span>
      <span class="field-label">套餐行程 <em>*</em></span>
      ${packages}
      <span class="field-error" data-error-for="itineraries"></span>
    </div>
  </details>`;
}

function refreshNodeButtons(form) {
  form.querySelectorAll('[data-node-list]').forEach((list) => {
    const count = list.children.length;
    list.querySelectorAll('[data-remove-node]').forEach((button) => {
      button.disabled = count <= 3;
    });
  });
  form.querySelectorAll('[data-add-node]').forEach((button) => {
    const list = form.querySelector(`[data-node-list="${button.dataset.addNode}"]`);
    button.disabled = !list || list.children.length >= 5;
  });
}

export function bindDraftEditor(form) {
  form.addEventListener('click', (event) => {
    const add = event.target.closest('[data-add-node]');
    if (add) {
      const list = form.querySelector(`[data-node-list="${add.dataset.addNode}"]`);
      if (list && list.children.length < 5) list.append(nodeRow());
      refreshNodeButtons(form);
      return;
    }
    const remove = event.target.closest('[data-remove-node]');
    if (!remove) return;
    const row = remove.closest('.itinerary-node');
    const list = row?.parentElement;
    if (list && list.children.length > 3) row.remove();
    refreshNodeButtons(form);
  });
  refreshNodeButtons(form);
}

export function readDraft(form) {
  const highlights = [...form.querySelectorAll('[data-highlight-index]')]
    .sort((a, b) => Number(a.dataset.highlightIndex) - Number(b.dataset.highlightIndex))
    .map((input) => input.value);
  const itineraries = {};
  for (const pkg of DRAFT_PACKAGES) {
    const list = form.querySelector(`[data-node-list="${pkg.key}"]`);
    itineraries[pkg.key] = [...(list?.querySelectorAll('.itinerary-node') || [])].map((row) => ({
      time: row.querySelector('[data-node-time]').value,
      place: row.querySelector('[data-node-place]').value,
      activity: row.querySelector('[data-node-activity]').value
    }));
  }
  return { highlights, itineraries };
}

export function applyDraft(form, draft) {
  if (typeof draft?.bio === 'string' && form.elements.bio) {
    form.elements.bio.value = draft.bio;
    form.elements.bio.dispatchEvent(new Event('input', { bubbles: true }));
  }
  if (Array.isArray(draft?.highlights)) {
    const inputs = [...form.querySelectorAll('[data-highlight-index]')].sort(
      (a, b) => Number(a.dataset.highlightIndex) - Number(b.dataset.highlightIndex)
    );
    inputs.forEach((input, index) => {
      input.value = draft.highlights[index] == null ? '' : String(draft.highlights[index]);
    });
  }
  const routes = draft?.itineraries;
  if (routes && typeof routes === 'object') {
    for (const pkg of DRAFT_PACKAGES) {
      const nodes = routes[pkg.key];
      const list = form.querySelector(`[data-node-list="${pkg.key}"]`);
      if (!list || !Array.isArray(nodes)) continue;
      const rows = nodes.slice(0, 5).map((node) => nodeRow(node));
      while (rows.length < 3) rows.push(nodeRow());
      list.replaceChildren(...rows);
    }
  }
  const editor = form.querySelector('[data-draft-editor]');
  if (editor) editor.open = true;
  refreshNodeButtons(form);
}

function blockShell(title, hint, part) {
  const block = document.createElement('section');
  block.className = 'ai-draft-block';
  block.dataset.draftBlock = part;
  block.innerHTML = `<div class="ai-draft-block-head">
      <div><strong></strong><small></small></div>
      <button type="button" class="btn btn--ghost btn--sm" data-draft-retry="${part}">换一版 ${icon('sparkles')}</button>
    </div>
    <div class="ai-draft-block-body"></div>
    <p class="ai-draft-block-status" hidden></p>`;
  block.querySelector('strong').textContent = title;
  block.querySelector('small').textContent = hint;
  return block;
}

function fillBlock(block, node) {
  const body = block.querySelector('.ai-draft-block-body');
  body.replaceChildren(node);
}

export function openDraftModal({ notes = '', city = '', services = [], onApply }) {
  if (!city) {
    toast('请先选择你生活的城市', 'info');
    return;
  }

  let notesValue = clipNotes(notes);
  const clipped = charLength(String(notes || '').trim()) > 300;
  let draft = null;
  let busy = false;
  let blockMessage = '';
  const variants = { all: 0, bio: 1, highlights: 1, itinerary: 1 };
  const chosen = [...new Set((services || []).filter((item) => typeof item === 'string' && item))];

  const modal = showModal(
    `<div class="ai-polish-modal ai-draft-modal">
      <div class="ai-polish-head">
        <span class="ai-orb">${icon('sparkles')}</span>
        <div>
          <span class="eyebrow">AI PROFILE DRAFT</span>
          <h2>两句话，写成一份主页</h2>
          <p>生成简介、三个亮点，以及半日、全天、傍晚各自的行程。你可以按块换一版，采用后还能改。</p>
        </div>
      </div>
      <div class="ai-polish-body" data-ai-body></div>
    </div>`,
    { className: 'modal--ai modal--ai-draft' }
  );
  const body = modal.dialog.querySelector('[data-ai-body]');

  const renderLoading = (label) => {
    body.innerHTML = `<div class="ai-loading">
      <span class="ai-loading-orb">${icon('sparkles')}</span>
      <strong></strong>
      <p>只用你写到的地点和经历</p>
      <span class="ai-loading-dots"><i></i><i></i><i></i></span>
    </div>`;
    body.querySelector('strong').textContent = label || '正在写成一份地陪主页…';
  };

  const renderProblem = (message) => {
    body.innerHTML = `<div class="ai-error ai-draft-error">
      <span>${icon('alert')}</span>
      <strong>这次没有生成成功</strong>
      <p data-draft-error></p>
      <label class="field">
        <span class="field-label">改一改再试 <small data-notes-count></small></span>
        <span class="input-wrap input-wrap--plain"><textarea data-draft-notes rows="4" maxlength="300"></textarea></span>
      </label>
      <button type="button" class="btn btn--primary btn--sm" data-draft-generate>再试一次</button>
    </div>`;
    body.querySelector('[data-draft-error]').textContent = message;
    const area = body.querySelector('[data-draft-notes]');
    area.value = notesValue;
    const count = body.querySelector('[data-notes-count]');
    const sync = () => {
      notesValue = area.value;
      count.textContent = `${charLength(area.value.trim())} / 300`;
    };
    area.addEventListener('input', sync);
    sync();
    body.querySelector('[data-draft-generate]').addEventListener('click', () => run('all'));
  };

  const renderNotes = (message = '') => {
    body.innerHTML = `<div class="ai-draft-notes">
      <label class="field">
        <span class="field-label">用两三句话写你的经历 <small data-notes-count></small></span>
        <span class="input-wrap input-wrap--plain">
          <textarea data-draft-notes rows="4" maxlength="300" placeholder="例如：我在成都长大，喜欢泡茶馆、吃苍蝇馆子，周末常去人民公园和玉林路。"></textarea>
        </span>
        <span class="field-hint">6 到 300 字。会连同你选的城市和服务类型一起生成。</span>
      </label>
      <p class="ai-draft-services" data-draft-services></p>
      <p class="field-hint" data-draft-clip hidden></p>
      <p class="field-error" data-draft-problem></p>
      <button type="button" class="btn btn--primary btn--full" data-draft-generate>生成草稿 ${icon('sparkles')}</button>
      <span class="ai-note">${icon('leaf')} 只用你写到的地点和经历，不会替你编造</span>
    </div>`;
    const area = body.querySelector('[data-draft-notes]');
    area.value = notesValue;
    const count = body.querySelector('[data-notes-count]');
    const sync = () => {
      notesValue = area.value;
      count.textContent = `${charLength(area.value.trim())} / 300`;
    };
    area.addEventListener('input', sync);
    sync();
    body.querySelector('[data-draft-services]').textContent = chosen.length
      ? `会一起带上的服务：${chosen.join('、')}`
      : '还没选服务类型。可以先在表单里勾上，亮点会更贴近你擅长的事。';
    const clip = body.querySelector('[data-draft-clip]');
    if (clipped) {
      clip.hidden = false;
      clip.textContent = '个人介绍超过 300 字，已先取前面的内容，可以再改。';
    }
    body.querySelector('[data-draft-problem]').textContent = message;
    body.querySelector('[data-draft-generate]').addEventListener('click', () => run('all'));
  };

  const renderDraft = () => {
    body.replaceChildren();
    const root = document.createElement('div');
    root.className = 'ai-draft-result';

    const bioBlock = blockShell('简介', '第一人称，采用后还能改', 'bio');
    const bio = document.createElement('div');
    bio.className = 'ai-result-text ai-draft-bio';
    bio.textContent = draft.bio || '';
    fillBlock(bioBlock, bio);

    const highlightBlock = blockShell('三个亮点', '正好三条，每条不超过 20 字', 'highlights');
    const highlights = document.createElement('ol');
    highlights.className = 'ai-draft-highlights';
    for (const item of draft.highlights || []) {
      const li = document.createElement('li');
      li.textContent = String(item ?? '');
      highlights.append(li);
    }
    fillBlock(highlightBlock, highlights);

    const routeBlock = blockShell('推荐行程', '半日、全天、傍晚各一条时间线', 'itinerary');
    const routes = document.createElement('div');
    routes.className = 'ai-draft-routes';
    for (const pkg of DRAFT_PACKAGES) {
      const group = document.createElement('div');
      group.className = 'ai-draft-route';
      const title = document.createElement('strong');
      title.textContent = `${pkg.name} · ${pkg.duration}`;
      group.append(title);
      const nodes = draft.itineraries?.[pkg.key];
      if (Array.isArray(nodes) && nodes.length) group.append(itineraryList(nodes));
      else {
        const empty = document.createElement('p');
        empty.textContent = '这一版没有这段行程';
        group.append(empty);
      }
      routes.append(group);
    }
    fillBlock(routeBlock, routes);

    const actions = document.createElement('div');
    actions.className = 'ai-actions';
    actions.innerHTML = `<button type="button" class="btn btn--primary" data-draft-apply>全部采用 ${icon('check')}</button>
      <button type="button" class="btn btn--ghost" data-draft-retry="all">全部换一版 ${icon('sparkles')}</button>`;

    const problem = document.createElement('p');
    problem.className = 'field-error ai-draft-problem';
    problem.textContent = blockMessage;

    const note = document.createElement('span');
    note.className = 'ai-note';
    note.innerHTML = `${icon('leaf')} `;
    const noteText = document.createElement('span');
    const local = engineNote(draft);
    noteText.textContent = `${local} · 只用你写到的地点和经历，不会替你编造`;
    note.append(noteText);

    root.append(bioBlock, highlightBlock, routeBlock, problem, actions, note);
    body.append(root);

    root.querySelectorAll('[data-draft-retry]').forEach((button) => {
      button.addEventListener('click', () => run(button.dataset.draftRetry));
    });
    root.querySelector('[data-draft-apply]').addEventListener('click', () => {
      const ready = validateItineraries(draft.itineraries);
      if (!ready.ok || !draft.bio || !Array.isArray(draft.highlights) || draft.highlights.length !== 3) {
        problem.textContent = ready.ok ? '草稿还不完整，请再生成一次。' : ready.message;
        return;
      }
      if (typeof onApply === 'function') {
        onApply({
          bio: draft.bio,
          highlights: draft.highlights.map((item) => String(item)),
          itineraries: ready.itineraries
        });
      }
      closeModal();
      toast('已填入简介、亮点和三个套餐的行程，还可以再改');
    });
  };

  const setBusy = (part, on) => {
    body.querySelectorAll('[data-draft-retry], [data-draft-apply], [data-draft-generate]').forEach((button) => {
      button.disabled = on;
    });
    const block = part && part !== 'all' ? body.querySelector(`[data-draft-block="${part}"]`) : null;
    if (!block) return;
    block.classList.toggle('is-busy', on);
    const status = block.querySelector('.ai-draft-block-status');
    status.hidden = !on;
    status.textContent = on ? '正在换一版…' : '';
  };

  const run = async (part) => {
    if (busy) return;
    const problem = notesProblem(notesValue);
    if (problem) {
      blockMessage = problem;
      if (draft && part !== 'all') renderDraft();
      else if (draft) renderProblem(problem);
      else renderNotes(problem);
      return;
    }
    busy = true;
    blockMessage = '';
    if (!draft || part === 'all') renderLoading(part === 'all' ? '正在写成一份地陪主页…' : '正在换一版…');
    else setBusy(part, true);
    try {
      const result = await api('/api/ai/profile-draft', {
        method: 'POST',
        body: {
          notes: notesValue.trim(),
          city,
          services: chosen,
          packages: DRAFT_PACKAGES.map(({ key, name, duration }) => ({ key, name, duration })),
          part,
          variant: variants[part] ?? 0
        }
      });
      if (!takeDraft(result, part)) {
        const message = '这次没有生成完整内容，请再试一次';
        if (draft && part !== 'all') {
          blockMessage = message;
          renderDraft();
        } else renderProblem(message);
        return;
      }
      variants[part] = variants[part] >= 20 ? 1 : variants[part] + 1;
      renderDraft();
    } catch (error) {
      const message = draftFailureMessage(error);
      if (draft && part !== 'all') {
        blockMessage = message;
        renderDraft();
      } else renderProblem(message);
    } finally {
      busy = false;
      setBusy(part, false);
    }
  };

  const takeDraft = (result, part) => {
    const next = draft
      ? { bio: draft.bio, highlights: draft.highlights, itineraries: draft.itineraries, provider: '', model: '', fallbackFrom: '' }
      : { bio: '', highlights: [], itineraries: null, provider: '', model: '', fallbackFrom: '' };
    if (part === 'all' || part === 'bio') {
      if (typeof result?.bio !== 'string' || !result.bio.trim()) return false;
      next.bio = result.bio;
    }
    if (part === 'all' || part === 'highlights') {
      if (!Array.isArray(result?.highlights) || result.highlights.length !== 3) return false;
      next.highlights = result.highlights.map((item) => String(item ?? ''));
    }
    if (part === 'all' || part === 'itinerary') {
      const check = validateItineraries(result?.itineraries);
      if (!check.ok) return false;
      next.itineraries = check.itineraries;
    }
    next.provider = result?.provider || result?.engine || '';
    next.model = result?.model || '';
    next.fallbackFrom = result?.fallbackFrom || '';
    draft = next;
    return true;
  };

  if (!notesProblem(notesValue)) run('all');
  else renderNotes();
}
