/** Pure checks for profile drafts. No DOM, so tests can import this module directly. */

export const DRAFT_PACKAGES = [
  { key: 'half', name: '半日轻游', duration: '4 小时', hours: 4 },
  { key: 'full', name: '全天深度游', duration: '8 小时', hours: 8 },
  { key: 'evening', name: '傍晚轻陪游', duration: '3 小时', hours: 3 }
];

const TIME_RE = /^([01]\d|2[0-3]):([0-5]\d)$/;

export function charLength(value) {
  return Array.from(String(value ?? '')).length;
}

export function notesProblem(notes) {
  const length = charLength(String(notes ?? '').trim());
  if (length < 6 || length > 300) return '请写 6 到 300 字，方便生成简介和行程';
  return '';
}

export function draftFailureMessage(error) {
  const status = Number.isInteger(error?.status) ? error.status : 0;
  const server = typeof error?.message === 'string' ? error.message.trim() : '';
  if (status === 429) return server || '生成太频繁，请稍后再试';
  if (status === 400) return server || '请写 6 到 300 字，并选好服务城市后再试';
  if (status === 401) return server || '请先登录';
  if (status === 0) return '网络好像开小差了，请稍后再试';
  return server || '生成没有成功，请稍后再试';
}

export function engineNote(result) {
  const provider = String(result?.provider || result?.engine || '');
  const fallback = String(result?.fallbackFrom || '');
  if (fallback) return '外部模型暂不可用，已改用本地 AI 引擎';
  if (!provider || provider === 'local') return '本地 AI 引擎';
  const model = result?.model ? ` · ${result.model}` : '';
  return `${provider}${model}`;
}

/** Traveler-facing nodes. Packages without an array `itinerary` contribute nothing. */
export function readPackageItinerary(pkg) {
  if (!pkg || typeof pkg !== 'object' || Array.isArray(pkg)) return [];
  if (!Array.isArray(pkg.itinerary)) return [];
  const nodes = [];
  for (const node of pkg.itinerary) {
    if (!node || typeof node !== 'object' || Array.isArray(node)) continue;
    const time = typeof node.time === 'string' ? node.time.trim() : '';
    const place = typeof node.place === 'string' ? node.place.trim() : '';
    const activity = typeof node.activity === 'string' ? node.activity.trim() : '';
    if (!time && !place && !activity) continue;
    nodes.push({ time, place, activity });
  }
  return nodes;
}

function cleanHighlight(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

export function validateHighlights(items) {
  const list = Array.isArray(items) ? items.map(cleanHighlight) : [];
  if (!list.length || list.every((item) => item === '')) return { ok: true, omit: true, highlights: [] };
  if (list.length !== 3 || list.some((item) => charLength(item) < 1 || charLength(item) > 20)) {
    return { ok: false, message: '亮点需要正好 3 条，每条 1 到 20 个字。' };
  }
  return { ok: true, omit: false, highlights: list };
}

function cleanTime(value) {
  const match = TIME_RE.exec(String(value ?? '').trim().replace('：', ':'));
  return match ? `${match[1]}:${match[2]}` : '';
}

function minutes(time) {
  const [hour, minute] = time.split(':').map(Number);
  return hour * 60 + minute;
}

function rowTouched(node) {
  if (!node || typeof node !== 'object') return false;
  return Boolean(String(node.time || '').trim() || String(node.place || '').trim() || String(node.activity || '').trim());
}

/**
 * Publish needs a timeline for every package. A missing package blocks submit.
 * Blank rows are ignored; a half-filled row is an error the guide can fix.
 */
export function validateItineraries(value) {
  const ask =
    '请为半日轻游、全天深度游和傍晚轻陪游都准备行程。每个套餐需要 3 到 5 个时间节点，也可以先点「AI 帮我写」。';
  if (!value || typeof value !== 'object' || Array.isArray(value)) return { ok: false, message: ask };
  const cleaned = {};
  for (const pkg of DRAFT_PACKAGES) {
    const nodes = value[pkg.key];
    if (!Array.isArray(nodes)) {
      return { ok: false, message: `还缺少「${pkg.name}」的行程。发布时半日、全天和傍晚三个套餐都要有时间线。` };
    }
    const filled = nodes.filter(rowTouched);
    if (!filled.length) {
      return { ok: false, message: `还缺少「${pkg.name}」的行程。发布时半日、全天和傍晚三个套餐都要有时间线。` };
    }
    if (filled.length < 3 || filled.length > 5) {
      return { ok: false, message: `「${pkg.name}」需要 3 到 5 个时间节点，现在是 ${filled.length} 个。` };
    }
    const normalized = [];
    for (const node of filled) {
      const time = cleanTime(node.time);
      const place = String(node.place ?? '').trim();
      const activity = String(node.activity ?? '').trim();
      if (!time || !place || !activity) {
        return { ok: false, message: `「${pkg.name}」里有没写完的节点，时间、地点和活动都要填。` };
      }
      if (charLength(place) > 20) return { ok: false, message: `「${pkg.name}」的地点需要 1 到 20 个字。` };
      if (charLength(activity) > 80) return { ok: false, message: `「${pkg.name}」的活动需要 1 到 80 个字。` };
      normalized.push({ time, place, activity });
    }
    const stamps = normalized.map((node) => minutes(node.time));
    if (stamps.some((later, index) => index > 0 && later <= stamps[index - 1])) {
      return { ok: false, message: `「${pkg.name}」的行程时间必须越来越晚。` };
    }
    if (stamps[stamps.length - 1] - stamps[0] > pkg.hours * 60) {
      return { ok: false, message: `「${pkg.name}」的行程超过了套餐的 ${pkg.duration}。` };
    }
    if (pkg.key === 'evening' && stamps[0] < 17 * 60) {
      return { ok: false, message: '傍晚轻陪游需要从 17:00 或更晚开始。' };
    }
    cleaned[pkg.key] = normalized;
  }
  return { ok: true, itineraries: cleaned };
}
