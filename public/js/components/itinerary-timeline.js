import { icon } from '../ui.js?v=1.7.0';

function nodeItem(node) {
  const item = document.createElement('li');
  const time = document.createElement('time');
  time.dateTime = node.time || '';
  time.textContent = node.time || '';
  const copy = document.createElement('div');
  const place = document.createElement('strong');
  place.textContent = node.place || '';
  const activity = document.createElement('span');
  activity.textContent = node.activity || '';
  copy.append(place, activity);
  item.append(time, copy);
  return item;
}

/** Always-visible timeline. Text is assigned with textContent, never interpolated into HTML. */
export function itineraryList(nodes) {
  const list = document.createElement('ol');
  list.className = 'itinerary-timeline';
  for (const node of nodes) list.append(nodeItem(node));
  return list;
}

/** Expandable package timeline. Renders nothing when there are no nodes. */
export function itineraryToggle(nodes) {
  if (!Array.isArray(nodes) || !nodes.length) return null;
  const wrap = document.createElement('div');
  wrap.className = 'package-itinerary';
  const list = itineraryList(nodes);
  list.hidden = true;
  const listId = `itinerary-${Math.random().toString(36).slice(2, 8)}`;
  list.id = listId;

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'itinerary-toggle';
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-controls', listId);
  button.innerHTML = `${icon('clock')}<span></span>${icon('chevron-down')}`;
  button.querySelector('span').textContent = '行程安排';
  button.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    const open = list.hidden;
    list.hidden = !open;
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    button.classList.toggle('is-open', open);
  });

  wrap.append(button, list);
  return wrap;
}
