// 游戏主界面 - 纯前端版（无后端）
let game = null;
let state = null;
let cachedShop = null;

// BUSH_POS / BLUE_TOWER_POS / RED_TOWER_POS / LANE_NAMES 均来自 game-core.js

async function init() {
  // 从 sessionStorage 恢复或从 URL 参数新建
  const saved = sessionStorage.getItem('hexlolfun_game');
  if (saved) {
    try {
      const obj = JSON.parse(saved);
      game = Game.fromJSON(obj);
    } catch (e) {
      game = null;
    }
  }
  if (!game) {
    const params = new URLSearchParams(location.search);
    const playerId = params.get('champ') || 'Yasuo';
    const ally = params.get('ally') || 'medium';
    const enemy = params.get('enemy') || 'medium';
    await loadGameData();
    // 读取设置中的 hex 版本
    const settings = (() => { try { return JSON.parse(sessionStorage.getItem('hexlolfun_settings') || '{}'); } catch(e){ return {}; } })();
    game = new Game(playerId, ally, enemy);
    game.hex_version = settings.hexVersion || '1.0';
    // 开局先派出一波小兵，让玩家看到兵线
    game.minion_wave_counter = 3;  // 强制下次 _spawnMinions 立即触发
    game._spawnMinions();
    game._processMinionMovement();
    persist();
  }
  state = game.serialize();
  render();
  bindEvents();
}

function persist() {
  try {
    sessionStorage.setItem('hexlolfun_game', JSON.stringify(game.toJSON()));
  } catch (e) {
    // 超出存储限制，忽略
  }
}

function refresh() {
  state = game.serialize();
  render();
  persist();
}

function render() {
  // 时间
  const t = state.game_time;
  document.getElementById('game-time').textContent =
    `${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;
  document.getElementById('round-num').textContent = state.round;
  document.getElementById('game-status').textContent =
    state.game_over ? (state.winner === 'blue' ? '🏆 蓝方胜利' : '💀 蓝方失败') : '战斗中';

  // 玩家
  const player = state.champions.find(c => c.id === state.player_id);
  renderPlayer(player);
  renderTeams();

  // 地图
  renderMap();
  renderLaneStrip();

  // 战报
  renderLog();

  // 商店
  renderShop();

  // 海克斯
  if (state.pending_hex) {
    renderHexSelection();
  } else {
    document.getElementById('hex-panel').innerHTML = '';
  }
  if (state.game_over) {
    showGameOverModal();
  }
}

function renderPlayer(p) {
  const hpPct = p.max_hp > 0 ? (p.hp / p.max_hp * 100) : 0;
  const isDead = !p.alive;
  const panel = document.getElementById('player-panel');
  panel.innerHTML = `
    <h3>👤 玩家</h3>
    <div class="player-card">
      <img class="player-portrait" src="${p.square_url}" onerror="this.style.display='none'">
      <div class="player-info">
        <div class="player-name">${p.name}<span class="player-level">LV.${p.level}</span></div>
        <div style="color:var(--text-secondary);font-size:0.75rem">${p.title}</div>
        <div class="player-stats">
          <div class="stat">❤️ ${Math.round(p.hp)}/${Math.round(p.max_hp)}</div>
          <div class="stat">🗡️ ${p.ad} AD</div>
          <div class="stat">🔮 ${p.ap} AP</div>
          <div class="stat">🛡️ ${p.armor} 护甲</div>
          <div class="stat">⚡ ${p.attack_speed} 攻速</div>
          <div class="stat">💨 ${p.move_speed} 移速</div>
          <div class="stat">💰 ${p.gold}G</div>
          <div class="stat">📍 ${p.position_name}</div>
        </div>
        <div class="hp-bar"><div class="hp-bar-fill ${hpPct < 30 ? 'low' : ''}" style="width:${hpPct}%"></div></div>
        <div class="kda">K/D/A: ${p.kills}/${p.deaths}/${p.assists}${isDead ? ` · 💀 复活中 ${p.respawn_timer}s` : ''}</div>
        ${p.items.length ? `<div class="player-items">${p.items.map(i => `<span class="item-tag">${i}</span>`).join('')}</div>` : ''}
        ${p.hex_augments.length ? `<div class="player-hexes">${p.hex_augments.map(h => `<span class="hex-tag">${h}</span>`).join('')}</div>` : ''}
      </div>
    </div>
  `;
}

function renderTeams() {
  const allies = state.champions.filter(c => c.team === 'blue' && c.id !== state.player_id);
  const enemies = state.champions.filter(c => c.team === 'red');
  const panel = document.getElementById('team-panel');
  panel.innerHTML = `
    <h3>🤝 友方 (${allies.filter(a => a.alive).length}/4)</h3>
    <div class="team-list">${allies.map(a => renderTeamRow(a, 'ally')).join('')}</div>
    <h3 style="margin-top:0.8rem">👹 敌方 (${enemies.filter(e => e.alive).length}/5)</h3>
    <div class="team-list">${enemies.map(e => renderTeamRow(e, 'enemy')).join('')}</div>
  `;
}

function renderTeamRow(c, type) {
  return `
    <div class="team-row ${c.alive ? '' : 'dead'}">
      <img class="${type === 'ally' ? 'tr-portrait-ally' : 'tr-portrait-enemy'}"
           src="${c.square_url}" onerror="this.style.display='none'">
      <span class="tr-name">${c.name}</span>
      <span class="tr-lv">L${c.level}</span>
      <span class="tr-hp">${c.alive ? Math.round(c.hp) + '/' + Math.round(c.max_hp) : '💀' + c.respawn_timer + 's'}</span>
    </div>
  `;
}

function renderMap() {
  const positions = Array.from({length: 16}, () => ({
    heroes: [], minions_blue: 0, minions_red: 0,
    tower_blue: null, tower_red: null,
    nexus_blue: null, nexus_red: null,
    inhib_blue: null, inhib_red: null,
  }));

  for (const c of state.champions) {
    if (c.alive) positions[c.position].heroes.push(c);
  }
  for (const m of state.minions) {
    if (m.team === 'blue') positions[m.position].minions_blue++;
    else positions[m.position].minions_red++;
  }
  for (const t of state.blue_towers) {
    if (t.alive) positions[t.position].tower_blue = t;
  }
  for (const t of state.red_towers) {
    if (t.alive) positions[t.position].tower_red = t;
  }
  positions[2].inhib_blue = state.blue_inhib;
  positions[13].inhib_red = state.red_inhib;
  positions[0].nexus_blue = state.blue_nexus;
  positions[15].nexus_red = state.red_nexus;

  const playerPos = state.champions.find(c => c.id === state.player_id).position;

  const renderIconsRow = (row) => row.map(i => {
    const p = positions[i];
    const isPlayer = i === playerPos;
    let icons = '';
    for (const c of p.heroes) {
      const cls = c.id === state.player_id ? 'player-icon' : (c.team === 'blue' ? 'ally-icon' : 'enemy-icon');
      icons += `<img class="unit-icon ${cls}" src="${c.square_url}" title="${c.name} Lv.${c.level}" onerror="this.style.display='none'">`;
    }
    if (p.tower_blue) {
      icons += `<div class="tower-icon blue-tower" title="${p.tower_blue.name} ${p.tower_blue.hp}/${p.tower_blue.max_hp}">🛡</div>`;
    }
    if (p.tower_red) {
      icons += `<div class="tower-icon red-tower" title="${p.tower_red.name} ${p.tower_red.hp}/${p.tower_red.max_hp}">🛡</div>`;
    }
    if (p.inhib_blue && p.inhib_blue.alive) {
      icons += `<div class="tower-icon blue-tower" title="蓝方水晶 ${p.inhib_blue.hp}/${p.inhib_blue.max_hp}">💎</div>`;
    }
    if (p.inhib_red && p.inhib_red.alive) {
      icons += `<div class="tower-icon red-tower" title="红方水晶 ${p.inhib_red.hp}/${p.inhib_red.max_hp}">💎</div>`;
    }
    if (p.nexus_blue && p.nexus_blue.alive) {
      icons += `<div class="tower-icon blue-tower" title="蓝方基地 ${p.nexus_blue.hp}/5000">🏛</div>`;
    }
    if (p.nexus_red && p.nexus_red.alive) {
      icons += `<div class="tower-icon red-tower" title="红方基地 ${p.nexus_red.hp}/5000">🏛</div>`;
    }
    for (let n = 0; n < Math.min(p.minions_blue, 4); n++) {
      icons += `<div class="unit-icon minion-b" title="蓝方小兵">⚔</div>`;
    }
    for (let n = 0; n < Math.min(p.minions_red, 4); n++) {
      icons += `<div class="unit-icon minion-r" title="红方小兵">⚔</div>`;
    }
    if (p.minions_blue > 4) icons += `<span style="color:var(--blue-team);font-size:0.7rem">+${p.minions_blue - 4}</span>`;
    if (p.minions_red > 4) icons += `<span style="color:var(--red-team);font-size:0.7rem">+${p.minions_red - 4}</span>`;
    return `<div class="lane-pos ${isPlayer ? 'player' : ''}">${icons || '<span style="color:#333;font-size:0.7rem">空</span>'}</div>`;
  }).join('');

  const html =
    `<div class="map-row map-row-blue">${renderIconsRow(MAP_ROW_BLUE)}</div>` +
    `<div class="map-row map-row-mid">${renderIconsRow(MAP_ROW_MID)}</div>` +
    `<div class="map-row map-row-red">${renderIconsRow(MAP_ROW_RED)}</div>`;
  document.getElementById('map').innerHTML = html;
}

// 地图分 3 行：
//   蓝方半场：0-5 (6 格：基地→外草丛)
//   河道：6-9 (4 格：外塔/草丛①/草丛②/外塔)
//   红方半场：10-15 (6 格：外草丛→基地)
const MAP_ROW_BLUE = [0, 1, 2, 3, 4, 5];
const MAP_ROW_MID  = [6, 7, 8, 9];
const MAP_ROW_RED  = [10, 11, 12, 13, 14, 15];

function renderLaneStrip() {
  const playerPos = state.champions.find(c => c.id === state.player_id).position;
  const renderRow = (row) => row.map(i => {
    let cls = 'lane-cell';
    if (BUSH_POS.includes(i)) cls += ' bush';
    if (BLUE_TOWER_POS.includes(i)) cls += ' tower-blue';
    if (RED_TOWER_POS.includes(i)) cls += ' tower-red';
    if (MAP_ROW_BLUE.includes(i)) cls += ' side-blue';
    if (MAP_ROW_RED.includes(i)) cls += ' side-red';
    if (MAP_ROW_MID.includes(i)) cls += ' side-mid';
    if (i === playerPos) cls += ' player-here';
    return `<div class="${cls}">${i}. ${LANE_NAMES[i]}</div>`;
  }).join('');
  document.getElementById('map-row-blue').innerHTML = renderRow(MAP_ROW_BLUE);
  document.getElementById('map-row-mid').innerHTML = renderRow(MAP_ROW_MID);
  document.getElementById('map-row-red').innerHTML = renderRow(MAP_ROW_RED);
}

function renderLog() {
  const list = document.getElementById('log-list');
  list.innerHTML = state.action_log.slice(-50).reverse().map(line => {
    let cls = 'log-entry';
    if (line.includes('击杀') || line.includes('阵亡')) cls += ' kill';
    else if (line.includes('海克斯')) cls += ' hex';
    else if (line.includes('摧毁') || line.includes('塔')) cls += ' tower';
    return `<div class="${cls}">${escapeHtml(line)}</div>`;
  }).join('');
}

function renderShop() {
  const player = state.champions.find(c => c.id === state.player_id);
  const panel = document.getElementById('shop-panel');
  if (!player.can_shop) {
    panel.innerHTML = `<h3>🛒 商店</h3><div class="shop-locked">死亡后才能购买</div>`;
    return;
  }
  const items = game.getShopItems();
  let html = `<h3>🛒 商店 (${player.gold}G)</h3><div class="shop-list">`;
  let lastCat = '';
  for (const item of items) {
    if (item.category !== lastCat) {
      if (lastCat) html += `</div>`;
      html += `<div class="shop-cat">${item.category}</div>`;
      lastCat = item.category;
    }
    html += `<div class="shop-item ${item.owned ? 'owned' : ''}" data-name="${escapeHtml(item.name)}">
      <span class="item-name">${item.owned ? '✓ ' : ''}${escapeHtml(item.name)}</span>
      <span class="item-price">${item.price}G</span>
    </div>`;
  }
  html += `</div>`;
  panel.innerHTML = html;
  panel.querySelectorAll('.shop-item').forEach(el => {
    el.onclick = () => buyItem(el.dataset.name);
  });
}

function renderHexSelection() {
  const p = state.pending_hex;
  const panel = document.getElementById('hex-panel');
  if (!p) { panel.innerHTML = ''; return; }
  let html = `<h3>🔮 海克斯选择 (${p.quality})</h3>
    <div style="color:var(--text-secondary);font-size:0.75rem;margin-bottom:0.4rem">点击选择一项强化</div>
    <div class="hex-options">`;
  p.options.forEach((opt, i) => {
    html += `<div class="hex-option" data-idx="${i}">
      <div class="hex-quality">${p.quality}海克斯 · 选项 ${i+1}</div>
      ${escapeHtml(opt)}
    </div>`;
  });
  html += `</div>`;
  panel.innerHTML = html;
  panel.querySelectorAll('.hex-option').forEach(el => {
    el.onclick = () => selectHex(parseInt(el.dataset.idx));
  });
}

// ============= 动作 =============
function doAction(action) {
  if (state.pending_hex) {
    alert('请先选择海克斯！');
    return;
  }
  if (state.game_over) return;
  game.processRound(action);
  refresh();
}

function buyItem(name) {
  const result = game.buyItem(name);
  if (!result.ok) {
    alert(result.msg);
    return;
  }
  alert(result.msg);
  refresh();
}

function selectHex(idx) {
  const result = game.selectHex(state.player_id, idx);
  if (result && !result.startsWith('获得')) {
    alert(result);
    return;
  }
  refresh();
}

function showGameOverModal() {
  const modal = document.getElementById('modal');
  const title = document.getElementById('modal-title');
  const desc = document.getElementById('modal-desc');
  if (state.winner === 'blue') {
    title.textContent = '🏆 蓝方胜利！';
    desc.textContent = '红方基地已被摧毁！';
  } else {
    title.textContent = '💀 蓝方失败';
    desc.textContent = '蓝方基地已被摧毁！';
  }
  modal.classList.remove('hidden');
}

function showHelp() {
  alert('操作说明：\nW - 前进一格\nS - 后退一格\nB - 回城\n蹲草 - 进入草丛\n待命 - 原地不动\n\n购买：死亡后点击商店\n海克斯：升级到 3/7/11/15 级时弹出选择');
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function bindEvents() {
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key.toLowerCase();
    if (k === 'w') doAction('w');
    else if (k === 's') doAction('s');
    else if (k === 'b') doAction('b');
    else if (k === ' ') { e.preventDefault(); doAction('待命'); }
  });
}

init();
