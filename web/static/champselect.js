// 选人页逻辑（纯前端版）
let allChamps = [];
let selectedChamp = null;
let activeFilter = 'all';
let gameDataReady = false;

const TAGS = ['all', 'Fighter', 'Mage', 'Assassin', 'Tank', 'Marksman', 'Support'];

async function init() {
  // 等待数据加载
  await loadGameData();
  gameDataReady = true;
  allChamps = ALL_CHAMPIONS;
  renderFilterTags();
  renderGrid(allChamps);
  bindEvents();
}

function renderFilterTags() {
  const container = document.getElementById('filter-tags');
  const tagName = { all: '全部', Fighter: '战士', Mage: '法师', Assassin: '刺客', Tank: '坦克', Marksman: '射手', Support: '辅助' };
  container.innerHTML = TAGS.map(t =>
    `<span data-tag="${t}" class="${t === activeFilter ? 'active' : ''}">${tagName[t] || t}</span>`
  ).join('');
  container.querySelectorAll('span').forEach(s => {
    s.onclick = () => {
      activeFilter = s.dataset.tag;
      container.querySelectorAll('span').forEach(x => x.classList.remove('active'));
      s.classList.add('active');
      applyFilters();
    };
  });
}

function applyFilters() {
  const q = document.getElementById('search').value.toLowerCase().trim();
  let filtered = allChamps;
  if (q) filtered = filtered.filter(c => c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q) || c.title.toLowerCase().includes(q));
  if (activeFilter !== 'all') filtered = filtered.filter(c => c.tags.includes(activeFilter));
  renderGrid(filtered);
}

function renderGrid(champs) {
  const grid = document.getElementById('champ-grid');
  grid.innerHTML = champs.map(c => `
    <div class="champ-card ${selectedChamp && selectedChamp.id === c.id ? 'selected' : ''}" data-id="${c.id}">
      <img src="${c.square_url}" alt="${c.name}" loading="lazy"
        onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzFhMWYyZSIvPjx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1zaXplPSIzMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iI2EwOWI4YyI+4oCUPC90ZXh0Pjwvc3ZnPg=='">
      <div class="name">${c.name}</div>
      <div class="tags-mini">${c.tags.join(' · ')}</div>
    </div>
  `).join('');
  grid.querySelectorAll('.champ-card').forEach(card => {
    card.onclick = () => {
      selectedChamp = allChamps.find(c => c.id === card.dataset.id);
      applyFilters();
      updateSelected();
    };
  });
}

function updateSelected() {
  const info = document.getElementById('selected-info');
  const btn = document.getElementById('start-btn');
  if (selectedChamp) {
    info.innerHTML = `
      <img src="${selectedChamp.square_url}" style="width:48px;height:48px;border-radius:4px;border:2px solid var(--gold-tier)">
      <div>
        <div style="color:var(--text-primary);font-weight:bold">${selectedChamp.name}</div>
        <div style="color:var(--text-secondary);font-size:0.8rem">${selectedChamp.title}</div>
      </div>
    `;
    btn.disabled = false;
  } else {
    info.innerHTML = '<span class="cs-empty">请从上方网格选择一名英雄</span>';
    btn.disabled = true;
  }
}

function bindEvents() {
  document.getElementById('search').addEventListener('input', applyFilters);
  document.getElementById('start-btn').onclick = () => {
    if (!selectedChamp) return;
    const params = new URLSearchParams({
      champ: selectedChamp.id,
      ally: document.getElementById('ally-diff').value,
      enemy: document.getElementById('enemy-diff').value,
    });
    window.location.href = 'loading.html?' + params;
  };
}

init();