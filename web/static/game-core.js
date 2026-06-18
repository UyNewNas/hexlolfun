// 海克斯大乱斗 5v5 文字版 — 纯前端游戏核心
// 对应 Python lolhex_simulator.py 的逻辑

// ============================================================
// 地图常量
// ============================================================
const BL_NEXUS = 0, BL_NEXUS_T = 1, BL_INHIB = 2, BL_INNER_BUSH = 3;
const BL_INNER_T = 4, BL_OUTER_BUSH = 5, BL_OUTER_T = 6, MID_BUSH1 = 7;
const MID_BUSH2 = 8, RD_OUTER_T = 9, RD_OUTER_BUSH = 10, RD_INNER_T = 11;
const RD_INNER_BUSH = 12, RD_INHIB = 13, RD_NEXUS_T = 14, RD_NEXUS = 15;

const LANE_NAMES = [
  "蓝方基地", "蓝方门牙塔", "蓝方水晶", "蓝方内塔后草丛",
  "蓝方内塔", "蓝方外塔后草丛", "蓝方外塔", "河道草丛①",
  "河道草丛②", "红方外塔", "红方外塔前草丛", "红方内塔",
  "红方内塔后草丛", "红方水晶", "红方门牙塔", "红方基地",
];
const BUSH_POS = [3, 5, 7, 8, 10, 12];
const BLUE_TOWER_POS = [1, 4, 6];
const RED_TOWER_POS = [9, 11, 14];
const ALL_TOWER_POS = [...BLUE_TOWER_POS, ...RED_TOWER_POS];

const TOWER_PREREQUISITE = {
  [BL_OUTER_T]: null, [BL_INNER_T]: BL_OUTER_T, [BL_INHIB]: BL_INNER_T,
  [BL_NEXUS_T]: BL_INHIB, [BL_NEXUS]: BL_NEXUS_T,
  [RD_OUTER_T]: null, [RD_INNER_T]: RD_OUTER_T, [RD_INHIB]: RD_INNER_T,
  [RD_NEXUS_T]: RD_INHIB, [RD_NEXUS]: RD_NEXUS_T,
};

const HEX_LEVELS = [3, 7, 11, 15];
const ROUND_DURATION = 10;
const MINION_WAVE_INTERVAL = 3;
const MINION_SPEED = 1;
const MINION_COMBAT_RANDOM = 0.3;
const XP_PER_KILL = 50;
const XP_PASSIVE = 5;
const LEVEL_CAP = 18;

// ============================================================
// 全局数据
// ============================================================
let ALL_CHAMPIONS = [];
let HEX_DATA = { 棱彩: [], 黄金: [], 白银: [] };
let EQUIPMENT_LIST = [];
let EQUIP_BY_CATEGORY = {};

// 加载静态数据
async function loadGameData() {
  const [c, h, e] = await Promise.all([
    fetch('data/champions.json').then(r => r.json()),
    fetch('data/hex.json').then(r => r.json()),
    fetch('data/equipments.json').then(r => r.json()),
  ]);
  ALL_CHAMPIONS = c;
  HEX_DATA = h;
  EQUIPMENT_LIST = e.all.map(eq => ({ name: eq[0], price: eq[1], category: eq[2], stats: eq[3] }));
  EQUIP_BY_CATEGORY = {};
  for (const cat of Object.keys(e.by_category)) {
    EQUIP_BY_CATEGORY[cat] = e.by_category[cat].map(eq => ({ name: eq[0], price: eq[1], category: eq[2], stats: eq[3] }));
  }
}

// ============================================================
// 工具
// ============================================================
function randChoice(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randSample(arr, n) {
  const copy = [...arr];
  const result = [];
  for (let i = 0; i < Math.min(n, copy.length); i++) {
    const idx = Math.floor(Math.random() * copy.length);
    result.push(copy.splice(idx, 1)[0]);
  }
  return result;
}

// ============================================================
// Champion 类
// ============================================================
class Champion {
  constructor(id, team, aiDifficulty) {
    const data = ALL_CHAMPIONS.find(c => c.id === id) || ALL_CHAMPIONS[0];
    this.id = data.id;
    this.name = data.name;
    this.title = data.title;
    this.tags = data.tags;
    this.square_url = data.square_url;
    this.splash_url = data.splash_url;

    this.team = team;
    this.ai_difficulty = aiDifficulty;
    // 玩家和友方AI从外塔出发；敌方AI从外塔出发（开局对峙不贴脸）
    this.position = team === 'blue' ? BL_OUTER_T : RD_OUTER_T;

    this.level = 1;
    this.exp = 0;
    this.gold = 500;
    this.kills = 0; this.deaths = 0; this.assists = 0;
    this.alive = true;
    this.respawn_timer = 0;
    this.can_shop = false;
    this.items = [];
    this.hex_augments = [];

    // 基础属性
    this.base_hp = data.base_hp;
    this.base_hp_per_level = data.hp_per_level;
    this.base_mp = data.base_mp;
    this.base_mp_per_level = data.mp_per_level;
    this.base_ad = data.base_ad;
    this.base_ad_per_level = data.ad_per_level;
    this.base_armor = data.base_armor;
    this.base_armor_per_level = data.armor_per_level;
    this.base_mr = data.base_mr;
    this.base_mr_per_level = data.mr_per_level;
    this.base_as = data.base_as;
    this.base_as_per_level = data.as_per_level;
    this.base_ms = data.base_ms;
    this.base_crit = data.base_crit;
    this.base_attack_range = data.attack_range;

    this.recalc_stats();
    this.hp = this.max_hp;
    this.mana = this.max_mana;
  }

  recalc_stats() {
    const lv = this.level;
    this.max_hp = this.base_hp + this.base_hp_per_level * (lv - 1);
    this.max_mana = this.base_mp + this.base_mp_per_level * (lv - 1);
    this.ad = this.base_ad + this.base_ad_per_level * (lv - 1);
    this.ap = 0;
    this.armor = this.base_armor + this.base_armor_per_level * (lv - 1);
    this.mr = this.base_mr + this.base_mr_per_level * (lv - 1);
    this.attack_speed = this.base_as + this.base_as_per_level / 100 * (lv - 1);
    this.move_speed = this.base_ms;
    this.crit = this.base_crit;
    this.attack_range = this.base_attack_range;

    for (const itemName of this.items) {
      this._applyItem(itemName);
    }
    // 海克斯效果（占位）

    this.hp = Math.min(this.hp ?? this.max_hp, this.max_hp);
    this.mana = Math.min(this.mana ?? this.max_mana, this.max_mana);
  }

  _applyItem(name) {
    const item = EQUIPMENT_LIST.find(e => e.name === name);
    if (!item) return;
    const s = item.stats;
    this.ad += s.ad || 0;
    this.ap += s.ap || 0;
    this.max_hp += s.hp || 0;
    this.armor += s.armor || 0;
    this.mr += s.mr || 0;
    this.attack_speed += s.attack_speed || 0;
    this.crit += s.crit || 0;
  }

  gain_exp(amount) {
    const oldLevel = this.level;
    this.exp += amount;
    while (this.level < LEVEL_CAP) {
      const need = 100 + this.level * 50;
      if (this.exp >= need) {
        this.exp -= need;
        this.level += 1;
        this.recalc_stats();
        if (this.alive) this.hp = this.max_hp;
      } else break;
    }
    return { oldLevel, newLevel: this.level };
  }

  getAttackRangeInPos() {
    if (this.attack_range <= 200) return 1;
    if (this.attack_range <= 500) return 2;
    return 3;
  }

  isDead() { return !this.alive; }
  respawn() {
    this.alive = true;
    this.hp = this.max_hp;
    this.can_shop = false;
    this.position = this.team === 'blue' ? BL_NEXUS : RD_NEXUS;
  }
}

// ============================================================
// Tower 类
// ============================================================
class Tower {
  constructor(position, team) {
    this.position = position;
    this.team = team;
    this.level = position === BL_NEXUS_T || position === RD_NEXUS_T ? 3 :
                 position === BL_INNER_T || position === RD_INNER_T ? 2 : 1;
    const cfg = { 1: {hp: 2000, ad: 180, armor: 60}, 2: {hp: 2500, ad: 210, armor: 60}, 3: {hp: 3000, ad: 250, armor: 80} };
    const c = cfg[this.level];
    this.max_hp = c.hp;
    this.hp = c.hp;
    this.attack_damage = c.ad;
    this.armor = c.armor;
    this.alive = true;
  }
  getName() {
    const prefix = this.team === 'blue' ? '蓝方' : '红方';
    const n = {1: '外塔', 2: '内塔', 3: '门牙塔'};
    return prefix + (n[this.level] || '塔');
  }
  getAttackRange() { return 2; }
}

// ============================================================
// Inhibitor 类
// ============================================================
class Inhibitor {
  constructor(position, team) {
    this.position = position; this.team = team;
    this.max_hp = 4000; this.hp = 4000; this.alive = true;
  }
  getName() { return (this.team === 'blue' ? '蓝方' : '红方') + '水晶'; }
}

// ============================================================
// Minion 类
// ============================================================
class Minion {
  constructor(team, position, hp, ad, isSiege = false) {
    this.team = team; this.position = position;
    this.max_hp = hp; this.hp = hp; this.ad = ad;
    this.alive = true; this.is_siege = isSiege;
  }
  getName() {
    return (this.team === 'blue' ? '蓝方' : '红方') + (this.is_siege ? '炮车' : '小兵');
  }
}

// ============================================================
// Team 类
// ============================================================
class Team {
  constructor(side, champions) {
    this.side = side;
    this.champions = champions;
    this.towers = {};
    this.inhibitor = null;
    this.nexus_alive = true;
  }
}

// ============================================================
// Game 主类
// ============================================================
class Game {
  constructor(playerId, allyDiff = 'medium', enemyDiff = 'medium') {
    this.round_count = 0;
    this.game_time = 0;
    this.action_log = [];
    this.minions = [];
    this.minion_wave_counter = 0;
    this.game_over = false;
    this.winner = null;
    this.nexus_hp = { [BL_NEXUS]: 5000, [RD_NEXUS]: 5000 };
    this._died_this_round = new Set();
    this.hex_level_order = ['棱彩', '黄金', '白银', '棱彩'];
    this.pending_hex = null;

    // 玩家
    this.player = new Champion(playerId, 'blue', '');
    // 友方AI - 分散在外塔和内塔之间（模仿真实对线站位）
    const allyIds = ['Garen', 'Lux', 'MasterYi', 'Annie'];
    const allyStartPos = [BL_OUTER_T, BL_INHIB, BL_OUTER_T, BL_INNER_T];
    this.ally_ai = allyIds.map((id, i) => {
      const c = new Champion(id, 'blue', allyDiff);
      c.position = allyStartPos[i];
      return c;
    });
    // 敌方AI - 分散在红方外塔和内塔
    const enemyIds = ['Darius', 'Ahri', 'Zed', 'Jinx', 'Leona'];
    const enemyStartPos = [RD_OUTER_T, RD_OUTER_T, RD_INNER_T, RD_INHIB, RD_OUTER_T];
    this.enemy_ai = enemyIds.map((id, i) => {
      const c = new Champion(id, 'red', enemyDiff);
      c.position = enemyStartPos[i];
      return c;
    });

    this.blue_team = new Team('blue', [this.player, ...this.ally_ai]);
    this.red_team = new Team('red', this.enemy_ai);

    // 塔
    for (const pos of BLUE_TOWER_POS) this.blue_team.towers[pos] = new Tower(pos, 'blue');
    for (const pos of RED_TOWER_POS) this.red_team.towers[pos] = new Tower(pos, 'red');
    // 水晶
    this.blue_team.inhibitor = new Inhibitor(BL_INHIB, 'blue');
    this.red_team.inhibitor = new Inhibitor(RD_INHIB, 'red');
  }

  log(msg) { this.action_log.push(msg); }
  getAllChampions() { return [this.player, ...this.ally_ai, ...this.enemy_ai]; }
  getTeam(side) { return side === 'blue' ? this.blue_team : this.red_team; }

  // ============= 回合主循环 =============
  processRound(playerAction = '') {
    this.action_log = [];
    this.round_count += 1;
    this._died_this_round = new Set();

    this._processPlayerAction(playerAction);
    this._processAIDecisions();
    this._spawnMinions();
    this._processMinionMovement();
    this._processCombat();
    this._processMinionCombat();
    this._processChampionsAttackTowers();
    this._processTowerAttacks();
    this._processDeaths();
    this._checkStructureDestruction();
    this.game_time += ROUND_DURATION;
    this._processPassiveGold();
    this._processPassiveExp();
    this._processLevelUpHex();
    this._checkWinCondition();
  }

  _processPlayerAction(action) {
    if (!action) return;
    const c = this.player;
    if (!c.alive) {
      this.log(`⏳ 你已阵亡，${c.respawn_timer}秒后复活`);
      return;
    }
    const parts = action.trim().toLowerCase().split(/\s+/);
    const cmd = parts[0];
    if (cmd === 'w' || cmd === '前进') {
      const move = (parts[1] && /^\d+$/.test(parts[1])) ? parseInt(parts[1]) : 1;
      const newPos = Math.min(RD_NEXUS, c.position + move);
      this.log(`▶ ${c.name} 前进了${move}格 → ${LANE_NAMES[newPos]}`);
      c.position = newPos;
    } else if (cmd === 's' || cmd === '后退') {
      const move = (parts[1] && /^\d+$/.test(parts[1])) ? parseInt(parts[1]) : 1;
      const newPos = Math.max(BL_NEXUS, c.position - move);
      this.log(`◀ ${c.name} 后退了${move}格 → ${LANE_NAMES[newPos]}`);
      c.position = newPos;
    } else if (cmd === 'b' || cmd === '回城') {
      c.position = c.team === 'blue' ? BL_NEXUS : RD_NEXUS;
      this.log(`🏠 ${c.name} 回城`);
    } else if (cmd === '蹲草') {
      if (BUSH_POS.includes(c.position)) this.log(`🌿 ${c.name} 进入草丛`);
      else this.log(`❌ 当前位置没有草丛`);
    } else if (cmd === '待命') {
      this.log(`⏸ ${c.name} 原地待命`);
    }
  }

  _processAIDecisions() {
    for (const c of this.getAllChampions()) {
      if (!c.alive || c.ai_difficulty === '') continue;
      if (c.ai_difficulty === 'easy') this._aiMoveForward(c);
      else if (c.ai_difficulty === 'medium') this._aiMedium(c);
      else if (c.ai_difficulty === 'hard') this._aiHard(c);
      else if (c.ai_difficulty === 'expert') this._aiExpert(c);
    }
  }

  _aiMoveForward(c) {
    if (c.team === 'blue' && c.position < RD_NEXUS) c.position += 1;
    else if (c.team === 'red' && c.position > BL_NEXUS) c.position -= 1;
  }

  _findNearestEnemy(c) {
    const enemyTeam = this.getTeam(c.team === 'blue' ? 'red' : 'blue');
    let nearest = null, minDist = 999;
    for (const e of enemyTeam.champions) {
      if (!e.alive) continue;
      const d = Math.abs(c.position - e.position);
      if (d < minDist) { minDist = d; nearest = e; }
    }
    return nearest;
  }

  _aiMedium(c) {
    const enemy = this._findNearestEnemy(c);
    if (!enemy) return;
    const dist = Math.abs(c.position - enemy.position);
    if (dist > c.getAttackRangeInPos()) {
      const step = c.team === 'blue' ? 1 : -1;
      const newPos = c.position + step;
      const enemyTowers = c.team === 'blue' ? RED_TOWER_POS : BLUE_TOWER_POS;
      if (!enemyTowers.includes(newPos)) c.position = newPos;
    }
  }

  _aiHard(c) {
    if (c.hp < c.max_hp * 0.3) {
      const step = c.team === 'blue' ? -1 : 1;
      c.position += step;
      return;
    }
    const enemyTeam = this.getTeam(c.team === 'blue' ? 'red' : 'blue');
    let lowest = null, lowestHp = 99999;
    for (const e of enemyTeam.champions) {
      if (!e.alive) continue;
      if (e.hp < lowestHp) { lowestHp = e.hp; lowest = e; }
    }
    if (lowest) {
      const dist = Math.abs(c.position - lowest.position);
      if (dist > c.getAttackRangeInPos()) {
        const step = c.team === 'blue' ? 1 : -1;
        const newPos = c.position + step;
        const enemyTowers = c.team === 'blue' ? RED_TOWER_POS : BLUE_TOWER_POS;
        if (!enemyTowers.includes(newPos)) c.position += step;
      }
    }
  }

  _aiExpert(c) {
    if (c.hp < c.max_hp * 0.35) {
      const step = c.team === 'blue' ? -1 : 1;
      c.position += step;
      return;
    }
    this._aiHard(c);
  }

  _spawnMinions() {
    this.minion_wave_counter += 1;
    if (this.minion_wave_counter < MINION_WAVE_INTERVAL) return;
    this.minion_wave_counter = 0;
    const waveNum = Math.floor(this.round_count / MINION_WAVE_INTERVAL);
    const hasSiege = waveNum > 0 && waveNum % 2 === 0;

    for (let i = 0; i < 4; i++) this.minions.push(new Minion('blue', BL_NEXUS, 350, 18));
    for (let i = 0; i < 3; i++) this.minions.push(new Minion('blue', BL_NEXUS, 220, 28));
    if (hasSiege) this.minions.push(new Minion('blue', BL_NEXUS, 900, 50, true));
    for (let i = 0; i < 4; i++) this.minions.push(new Minion('red', RD_NEXUS, 350, 18));
    for (let i = 0; i < 3; i++) this.minions.push(new Minion('red', RD_NEXUS, 220, 28));
    if (hasSiege) this.minions.push(new Minion('red', RD_NEXUS, 900, 50, true));

    const total = hasSiege ? 8 : 7;
    this.log(`⚔ 双方各派出${total}名小兵`);
  }

  _processMinionMovement() {
    const bluePos = new Set(this.minions.filter(m => m.alive && m.team === 'blue').map(m => m.position));
    const redPos = new Set(this.minions.filter(m => m.alive && m.team === 'red').map(m => m.position));
    for (const m of this.minions) {
      if (!m.alive) continue;
      if (m.team === 'blue') {
        const next = m.position + 1;
        if (next > RD_NEXUS) continue;
        if (redPos.has(next) || redPos.has(m.position)) continue;
        m.position = next;
      } else {
        const next = m.position - 1;
        if (next < BL_NEXUS) continue;
        if (bluePos.has(next) || bluePos.has(m.position)) continue;
        m.position = next;
      }
    }
  }

  _processCombat() {
    const all = this.getAllChampions();
    const pairs = new Set();
    for (const c of all) {
      if (!c.alive) continue;
      const range = c.getAttackRangeInPos();
      const enemyTeam = this.getTeam(c.team === 'blue' ? 'red' : 'blue');
      for (const e of enemyTeam.champions) {
        if (!e.alive) continue;
        const d = Math.abs(c.position - e.position);
        if (d <= range) {
          const pair = [c.id, e.id].sort().join('-');
          if (pairs.has(pair)) continue;
          pairs.add(pair);
          this._resolveAttack(c, e);
        }
      }
    }
    // 英雄vs小兵
    for (const c of all) {
      if (!c.alive) continue;
      const range = c.getAttackRangeInPos();
      const targets = this.minions.filter(m => m.alive && m.team !== c.team && Math.abs(m.position - c.position) <= range);
      if (!targets.length) continue;
      const target = targets.reduce((a, b) => a.hp < b.hp ? a : b);
      let dmg = Math.max(1, Math.floor(c.ad));
      if (Math.random() < c.crit) dmg = Math.floor(dmg * 1.75);
      target.hp -= dmg;
      if (target.hp <= 0) target.alive = false;
    }
  }

  _resolveAttack(attacker, defender) {
    const armor = defender.armor;
    const mult = 100 / (100 + armor);
    let dmg = Math.max(1, Math.floor(attacker.ad * mult));
    const crit = Math.random() < attacker.crit;
    if (crit) dmg = Math.floor(dmg * 1.75);
    defender.hp = Math.max(0, defender.hp - dmg);
    this.log(`💥 ${attacker.name} → ${defender.name} ${crit ? '暴击！' : ''} 造成${dmg}伤害 (${defender.hp}/${defender.max_hp})`);
  }

  _processMinionCombat() {
    const aliveMinions = this.minions.filter(m => m.alive);
    const blueFront = {}, redFront = {};
    for (const m of aliveMinions) {
      if (m.team === 'blue') (blueFront[m.position] = blueFront[m.position] || []).push(m);
      else (redFront[m.position] = redFront[m.position] || []).push(m);
    }
    const battles = new Set();
    for (const bp of Object.keys(blueFront)) {
      for (const rp of Object.keys(redFront)) {
        if (Math.abs(parseInt(bp) - parseInt(rp)) <= 1) {
          battles.add(`${bp}-${rp}`);
        }
      }
    }
    for (const key of battles) {
      const [bp, rp] = key.split('-').map(Number);
      const blueG = blueFront[bp] || [], redG = redFront[rp] || [];
      if (!blueG.length || !redG.length) continue;
      let blueAD = blueG.reduce((a, b) => a + b.ad, 0);
      let redAD = redG.reduce((a, b) => a + b.ad, 0);
      blueAD = Math.floor(blueAD * (1 + (Math.random() - 0.5) * 2 * MINION_COMBAT_RANDOM));
      redAD = Math.floor(redAD * (1 + (Math.random() - 0.5) * 2 * MINION_COMBAT_RANDOM));
      // 蓝方集火红方
      let dmg = blueAD;
      for (const m of [...redG].sort((a, b) => a.hp - b.hp)) {
        if (dmg <= 0 || !m.alive) break;
        const d = Math.min(dmg, m.hp);
        m.hp -= d; dmg -= d;
        if (m.hp <= 0) m.alive = false;
      }
      // 红方集火蓝方
      dmg = redAD;
      for (const m of [...blueG].sort((a, b) => a.hp - b.hp)) {
        if (dmg <= 0 || !m.alive) break;
        const d = Math.min(dmg, m.hp);
        m.hp -= d; dmg -= d;
        if (m.hp <= 0) m.alive = false;
      }
    }
    // 小兵攻击建筑
    for (const m of aliveMinions) {
      if (!m.alive) continue;
      if (m.team === 'blue') {
        if (RED_TOWER_POS.includes(m.position)) {
          const t = this.red_team.towers[m.position];
          if (t && t.alive) this._minionAttackTower(m, t);
        } else if (m.position === RD_INHIB && this.red_team.inhibitor.alive) {
          this._minionAttackBuilding(m, '红方水晶', this.red_team.inhibitor);
        } else if (m.position === RD_NEXUS) {
          this._minionAttackNexus(m, 'red');
        }
      } else {
        if (BLUE_TOWER_POS.includes(m.position)) {
          const t = this.blue_team.towers[m.position];
          if (t && t.alive) this._minionAttackTower(m, t);
        } else if (m.position === BL_INHIB && this.blue_team.inhibitor.alive) {
          this._minionAttackBuilding(m, '蓝方水晶', this.blue_team.inhibitor);
        } else if (m.position === BL_NEXUS) {
          this._minionAttackNexus(m, 'blue');
        }
      }
    }
  }

  _minionAttackTower(m, tower) {
    const prereq = TOWER_PREREQUISITE[tower.position];
    if (prereq) {
      const team = this.getTeam(m.team);
      if (team.towers[prereq] && team.towers[prereq].alive) return;
    }
    const mult = 100 / (100 + tower.armor);
    let dmg = m.ad * (m.is_siege ? 3 : 1);
    dmg = Math.max(1, Math.floor(dmg * mult));
    tower.hp -= dmg;
    const tag = m.is_siege ? '🚌' : '⚔';
    this.log(`${tag} ${m.getName()} → ${tower.getName()} 造成${dmg}伤害 (${tower.hp}/${tower.max_hp})`);
  }

  _minionAttackBuilding(m, name, building) {
    let dmg = m.ad * (m.is_siege ? 2 : 1);
    dmg = Math.max(1, Math.floor(dmg));
    building.hp -= dmg;
    if (building.hp <= 0) {
      building.alive = false;
      this.log(`💎 ${name} 被摧毁！（小兵）`);
    } else {
      const tag = m.is_siege ? '🚌' : '⚔';
      this.log(`${tag} ${m.getName()} → ${name} 造成${dmg}伤害 (${building.hp}/${building.max_hp})`);
    }
  }

  _minionAttackNexus(m, team) {
    const teamObj = this.getTeam(team);
    if (!teamObj.nexus_alive) return;
    let dmg = m.ad * (m.is_siege ? 2 : 1);
    dmg = Math.max(1, Math.floor(dmg));
    const pos = team === 'red' ? RD_NEXUS : BL_NEXUS;
    this.nexus_hp[pos] -= dmg;
    if (this.nexus_hp[pos] <= 0) {
      teamObj.nexus_alive = false;
      this.log(`🔥 ${team.toUpperCase()}方基地 被摧毁！（小兵）`);
    } else {
      const tag = m.is_siege ? '🚌' : '⚔';
      this.log(`${tag} ${m.getName()} → ${team === 'red' ? '红方' : '蓝方'}基地 造成${dmg}伤害 (${this.nexus_hp[pos]}/5000)`);
    }
  }

  _processChampionsAttackTowers() {
    for (const c of this.getAllChampions()) {
      if (!c.alive) continue;
      if (c.team === 'blue') {
        if (RED_TOWER_POS.includes(c.position)) {
          const t = this.red_team.towers[c.position];
          if (t && t.alive) this._championAttackTower(c, t);
        } else if (c.position === RD_INHIB && this.red_team.inhibitor.alive) {
          this._championAttackInhibitor(c, this.red_team.inhibitor, '红方水晶');
        } else if (c.position === RD_NEXUS) {
          this._championAttackNexus(c, 'red');
        }
      } else {
        if (BLUE_TOWER_POS.includes(c.position)) {
          const t = this.blue_team.towers[c.position];
          if (t && t.alive) this._championAttackTower(c, t);
        } else if (c.position === BL_INHIB && this.blue_team.inhibitor.alive) {
          this._championAttackInhibitor(c, this.blue_team.inhibitor, '蓝方水晶');
        } else if (c.position === BL_NEXUS) {
          this._championAttackNexus(c, 'blue');
        }
      }
    }
  }

  _championAttackTower(c, tower) {
    const prereq = TOWER_PREREQUISITE[tower.position];
    if (prereq) {
      const prereqTower = c.team === 'blue' ? this.red_team.towers[prereq] : this.blue_team.towers[prereq];
      if (prereqTower && prereqTower.alive) return;
    }
    const mult = 100 / (100 + tower.armor);
    const raw = c.ad * 0.8 + c.ap * 0.4;
    const dmg = Math.max(10, Math.floor(raw * mult));
    tower.hp -= dmg;
    this.log(`🔨 ${c.name} → ${tower.getName()} 造成${dmg}伤害 (${tower.hp}/${tower.max_hp})`);
  }

  _championAttackInhibitor(c, inhib, name) {
    const dmg = Math.max(10, Math.floor(c.ad * 0.6 + c.ap * 0.3));
    inhib.hp -= dmg;
    this.log(`🔨 ${c.name} → ${name} 造成${dmg}伤害 (${inhib.hp}/${inhib.max_hp})`);
  }

  _championAttackNexus(c, team) {
    const teamObj = this.getTeam(team);
    if (!teamObj.nexus_alive) return;
    const dmg = Math.max(10, Math.floor(c.ad * 0.6 + c.ap * 0.3));
    const pos = team === 'red' ? RD_NEXUS : BL_NEXUS;
    this.nexus_hp[pos] -= dmg;
    if (this.nexus_hp[pos] <= 0) {
      teamObj.nexus_alive = false;
      this.log(`🔥 ${team.toUpperCase()}方基地 被摧毁！（英雄）`);
    } else {
      this.log(`🔨 ${c.name} → ${team === 'red' ? '红方' : '蓝方'}基地 造成${dmg}伤害 (${this.nexus_hp[pos]}/5000)`);
    }
  }

  _processTowerAttacks() {
    for (const tower of Object.values(this.blue_team.towers)) {
      if (!tower.alive) continue;
      let target = null;
      for (const m of this.minions) {
        if (m.alive && m.team === 'red' && Math.abs(m.position - tower.position) <= tower.getAttackRange()) { target = m; break; }
      }
      if (!target) {
        for (const ec of this.red_team.champions) {
          if (ec.alive && Math.abs(ec.position - tower.position) <= tower.getAttackRange()) { target = ec; break; }
        }
      }
      if (target) {
        const dmg = tower.attack_damage;
        if (target instanceof Minion) {
          target.hp -= dmg;
          if (target.hp <= 0) target.alive = false;
          this.log(`🏛 ${tower.getName()} → ${target.getName()} 造成${dmg}伤害`);
        } else {
          target.hp = Math.max(0, target.hp - dmg);
          this.log(`🏛 ${tower.getName()} → ${target.name} 造成${dmg}伤害 (${target.hp}/${target.max_hp})`);
        }
      }
    }
    for (const tower of Object.values(this.red_team.towers)) {
      if (!tower.alive) continue;
      let target = null;
      for (const m of this.minions) {
        if (m.alive && m.team === 'blue' && Math.abs(m.position - tower.position) <= tower.getAttackRange()) { target = m; break; }
      }
      if (!target) {
        for (const ec of this.blue_team.champions) {
          if (ec.alive && Math.abs(ec.position - tower.position) <= tower.getAttackRange()) { target = ec; break; }
        }
      }
      if (target) {
        const dmg = tower.attack_damage;
        if (target instanceof Minion) {
          target.hp -= dmg;
          if (target.hp <= 0) target.alive = false;
          this.log(`🏛 ${tower.getName()} → ${target.getName()} 造成${dmg}伤害`);
        } else {
          target.hp = Math.max(0, target.hp - dmg);
          this.log(`🏛 ${tower.getName()} → ${target.name} 造成${dmg}伤害 (${target.hp}/${target.max_hp})`);
        }
      }
    }
  }

  _processDeaths() {
    for (const c of this.getAllChampions()) {
      if (c.alive && c.hp <= 0) {
        c.alive = false;
        c.deaths += 1;
        c.respawn_timer = c.level * 3;
        c.can_shop = true;
        this._died_this_round.add(c.id);
        this.log(`💀 ${c.name} 阵亡！${c.respawn_timer}秒后复活`);
        // 经验
        for (const mate of this.getTeam(c.team).champions) {
          if (mate.alive && Math.abs(mate.position - c.position) <= 3) {
            const { newLevel } = mate.gain_exp(XP_PER_KILL);
            if (newLevel > mate.level - 1) this.log(`⬆ ${mate.name} 升到${newLevel}级！`);
          }
        }
        // 击杀奖励
        const enemyTeam = this.getTeam(c.team === 'blue' ? 'red' : 'blue');
        let killer = null, minDist = 999;
        for (const ec of enemyTeam.champions) {
          if (ec.alive) {
            const d = Math.abs(ec.position - c.position);
            if (d < minDist) { minDist = d; killer = ec; }
          }
        }
        if (killer) {
          killer.gold += 300;
          killer.kills += 1;
          killer.gain_exp(XP_PER_KILL);
          this.log(`💰 ${killer.name} 获得 300G 击杀奖励`);
          for (const mate of this.getTeam(killer.team).champions) {
            if (mate.alive && mate.id !== killer.id && Math.abs(mate.position - c.position) <= 2) {
              mate.gold += 100;
              mate.assists += 1;
            }
          }
        }
      }
    }
    this.minions = this.minions.filter(m => m.alive && m.hp > 0);
  }

  _processPassiveGold() {
    for (const c of this.getAllChampions()) {
      if (c.alive) {
        c.gold += ROUND_DURATION;
      } else if (c.respawn_timer > 0) {
        if (this._died_this_round.has(c.id)) continue;
        c.respawn_timer -= ROUND_DURATION;
        if (c.respawn_timer <= 0) {
          c.respawn();
          this.log(`✨ ${c.name} 复活！`);
        }
      }
    }
  }

  _processPassiveExp() {
    for (const c of this.getAllChampions()) {
      if (c.alive && c.level < LEVEL_CAP) {
        const { newLevel } = c.gain_exp(XP_PASSIVE);
        if (newLevel > c.level - 1) this.log(`⬆ ${c.name} 升到${newLevel}级！`);
      }
    }
  }

  _processLevelUpHex() {
    for (const c of this.getAllChampions()) {
      if (!HEX_LEVELS.includes(c.level)) continue;
      const expectedIdx = HEX_LEVELS.indexOf(c.level);
      const actual = c.hex_augments.filter(h => h !== '__pending__');
      if (actual.length > expectedIdx) continue;
      if (c.hex_augments.includes('__pending__')) continue;
      const quality = this.hex_level_order[expectedIdx];
      const pool = HEX_DATA[quality] || [];
      if (!pool.length) continue;
      const options = randSample(pool, 3);
      if (c.id === this.player.id) {
        this.pending_hex = { champion_id: c.id, quality, options, level: c.level };
        c.hex_augments.push('__pending__');
        this.log(`🔮 你触发了海克斯选择！品质: ${quality}`);
        this.log(`   选项: ${options.join(' / ')}`);
      } else {
        const chosen = randChoice(options);
        c.hex_augments.push(chosen);
        c.recalc_stats();
        this.log(`🔮 ${c.name} 获得海克斯 [${quality}]: ${chosen}`);
      }
    }
  }

  selectHex(championId, optionIndex) {
    if (!this.pending_hex) return '当前没有待选择的海克斯';
    const p = this.pending_hex;
    if (p.champion_id !== championId) return '该英雄没有待选择的海克斯';
    if (optionIndex < 0 || optionIndex >= p.options.length) return '无效选项';
    const chosen = p.options[optionIndex];
    for (const c of this.getAllChampions()) {
      if (c.id === championId) {
        const idx = c.hex_augments.indexOf('__pending__');
        if (idx >= 0) c.hex_augments[idx] = chosen;
        else c.hex_augments.push(chosen);
        c.recalc_stats();
        this.log(`✅ ${c.name} 获得海克斯: ${chosen}`);
        break;
      }
    }
    this.pending_hex = null;
    return `获得海克斯: ${chosen}`;
  }

  _checkStructureDestruction() {
    for (const team of [this.blue_team, this.red_team]) {
      for (const tower of Object.values(team.towers)) {
        if (tower.alive && tower.hp <= 0) {
          tower.alive = false;
          this.log(`🏛 ${tower.getName()} 被摧毁！`);
        }
      }
      if (team.inhibitor.alive && team.inhibitor.hp <= 0) {
        team.inhibitor.alive = false;
        this.log(`💎 ${team.inhibitor.getName()} 被摧毁！`);
      }
      const nexusPos = team.side === 'blue' ? BL_NEXUS : RD_NEXUS;
      if (team.nexus_alive && this.nexus_hp[nexusPos] <= 0) {
        team.nexus_alive = false;
        this.log(`🔥 ${team.side.toUpperCase()}方基地 被摧毁！`);
      }
    }
  }

  _checkWinCondition() {
    if (!this.blue_team.nexus_alive) {
      this.game_over = true; this.winner = 'red';
      this.log('💥 红方胜利！蓝方基地被摧毁！');
    } else if (!this.red_team.nexus_alive) {
      this.game_over = true; this.winner = 'blue';
      this.log('💥 蓝方胜利！红方基地被摧毁！');
    }
  }

  // ============= 商店 =============
  getShopItems() {
    const result = [];
    for (const cat of ['基础', 'AD', 'AP', '坦克', '鞋子']) {
      const items = EQUIP_BY_CATEGORY[cat] || [];
      for (const item of items) {
        result.push({ ...item, category: cat, owned: this.player.items.includes(item.name) });
      }
    }
    return result;
  }

  buyItem(itemName) {
    if (!this.player.can_shop) return { ok: false, msg: '只有阵亡时才能购买' };
    const item = EQUIPMENT_LIST.find(e => e.name === itemName);
    if (!item) return { ok: false, msg: '无效物品' };
    if (this.player.gold < item.price) return { ok: false, msg: `金币不足！需要${item.price}G，你有${this.player.gold}G` };
    this.player.gold -= item.price;
    this.player.items.push(itemName);
    this.player.recalc_stats();
    return { ok: true, msg: `购买了 ${itemName}！` };
  }

  // ============= 序列化（供前端使用） =============
  serialize() {
    return {
      round: this.round_count,
      game_time: this.game_time,
      game_over: this.game_over,
      winner: this.winner,
      player_id: this.player.id,
      champions: this.getAllChampions().map(c => this._serializeChamp(c)),
      blue_towers: Object.values(this.blue_team.towers).map(t => ({
        position: t.position, level: t.level, alive: t.alive,
        hp: t.hp, max_hp: t.max_hp, name: t.getName(),
      })),
      red_towers: Object.values(this.red_team.towers).map(t => ({
        position: t.position, level: t.level, alive: t.alive,
        hp: t.hp, max_hp: t.max_hp, name: t.getName(),
      })),
      blue_inhib: { alive: this.blue_team.inhibitor.alive, hp: this.blue_team.inhibitor.hp, max_hp: this.blue_team.inhibitor.max_hp },
      red_inhib: { alive: this.red_team.inhibitor.alive, hp: this.red_team.inhibitor.hp, max_hp: this.red_team.inhibitor.max_hp },
      blue_nexus: { alive: this.blue_team.nexus_alive, hp: this.nexus_hp[BL_NEXUS], max_hp: 5000 },
      red_nexus: { alive: this.red_team.nexus_alive, hp: this.nexus_hp[RD_NEXUS], max_hp: 5000 },
      minions: this.minions.filter(m => m.alive).map(m => ({ team: m.team, position: m.position, is_siege: m.is_siege })),
      action_log: this.action_log.slice(-50),
      pending_hex: this.pending_hex,
    };
  }

  _serializeChamp(c) {
    return {
      id: c.id, name: c.name, title: c.title, level: c.level, exp: c.exp,
      gold: c.gold, kills: c.kills, deaths: c.deaths, assists: c.assists,
      position: c.position, position_name: LANE_NAMES[c.position],
      team: c.team, alive: c.alive, respawn_timer: c.respawn_timer,
      hp: c.hp, max_hp: c.max_hp, mana: c.mana, max_mana: c.max_mana,
      ad: Math.round(c.ad * 10) / 10, ap: Math.round(c.ap * 10) / 10,
      armor: Math.round(c.armor * 10) / 10, mr: Math.round(c.mr * 10) / 10,
      attack_speed: Math.round(c.attack_speed * 100) / 100,
      move_speed: c.move_speed, crit: Math.round(c.crit * 100) / 100,
      items: c.items,
      hex_augments: c.hex_augments.filter(h => h !== '__pending__'),
      can_shop: c.can_shop,
      square_url: c.square_url, splash_url: c.splash_url,
    };
  }

  // ============= 序列化/反序列化（保存到 sessionStorage） =============
  toJSON() {
    return {
      round_count: this.round_count,
      game_time: this.game_time,
      game_over: this.game_over,
      winner: this.winner,
      nexus_hp: { ...this.nexus_hp },
      minions: this.minions.map(m => ({
        team: m.team, position: m.position, hp: m.hp, max_hp: m.max_hp, ad: m.ad, is_siege: m.is_siege, alive: m.alive
      })),
      minion_wave_counter: this.minion_wave_counter,
      pending_hex: this.pending_hex,
      hex_level_order: this.hex_level_order,
      player: this._champToJSON(this.player),
      ally_ai: this.ally_ai.map(c => this._champToJSON(c)),
      enemy_ai: this.enemy_ai.map(c => this._champToJSON(c)),
      blue_towers: Object.values(this.blue_team.towers).map(t => ({
        position: t.position, level: t.level, alive: t.alive,
        hp: t.hp, max_hp: t.max_hp,
      })),
      red_towers: Object.values(this.red_team.towers).map(t => ({
        position: t.position, level: t.level, alive: t.alive,
        hp: t.hp, max_hp: t.max_hp,
      })),
      blue_inhib: { alive: this.blue_team.inhibitor.alive, hp: this.blue_team.inhibitor.hp, max_hp: this.blue_team.inhibitor.max_hp },
      red_inhib: { alive: this.red_team.inhibitor.alive, hp: this.red_team.inhibitor.hp, max_hp: this.red_team.inhibitor.max_hp },
      blue_nexus_alive: this.blue_team.nexus_alive,
      red_nexus_alive: this.red_team.nexus_alive,
    };
  }

  _champToJSON(c) {
    return {
      id: c.id, team: c.team, ai_difficulty: c.ai_difficulty,
      level: c.level, exp: c.exp, gold: c.gold,
      kills: c.kills, deaths: c.deaths, assists: c.assists,
      position: c.position, alive: c.alive, respawn_timer: c.respawn_timer,
      can_shop: c.can_shop, items: [...c.items], hex_augments: [...c.hex_augments],
    };
  }

  static fromJSON(data) {
    if (typeof ALL_CHAMPIONS === 'undefined' || !ALL_CHAMPIONS.length) {
      throw new Error('ALL_CHAMPIONS not loaded yet');
    }
    const g = Object.create(Game.prototype);
    g.round_count = data.round_count;
    g.game_time = data.game_time;
    g.game_over = data.game_over;
    g.winner = data.winner;
    g.nexus_hp = { ...data.nexus_hp };
    g.minion_wave_counter = data.minion_wave_counter;
    g.pending_hex = data.pending_hex;
    g.hex_level_order = data.hex_level_order;
    g.action_log = [];
    g._died_this_round = new Set();

    g.player = Game._restoreChamp(data.player);
    g.ally_ai = data.ally_ai.map(c => Game._restoreChamp(c));
    g.enemy_ai = data.enemy_ai.map(c => Game._restoreChamp(c));

    g.blue_team = new Team('blue', [g.player, ...g.ally_ai]);
    g.red_team = new Team('red', g.enemy_ai);

    for (const t of data.blue_towers) {
      const tower = new Tower(t.position, 'blue');
      tower.hp = t.hp; tower.alive = t.alive;
      g.blue_team.towers[t.position] = tower;
    }
    for (const t of data.red_towers) {
      const tower = new Tower(t.position, 'red');
      tower.hp = t.hp; tower.alive = t.alive;
      g.red_team.towers[t.position] = tower;
    }
    g.blue_team.inhibitor = new Inhibitor(BL_INHIB, 'blue');
    g.blue_team.inhibitor.hp = data.blue_inhib.hp;
    g.blue_team.inhibitor.alive = data.blue_inhib.alive;
    g.red_team.inhibitor = new Inhibitor(RD_INHIB, 'red');
    g.red_team.inhibitor.hp = data.red_inhib.hp;
    g.red_team.inhibitor.alive = data.red_inhib.alive;
    g.blue_team.nexus_alive = data.blue_nexus_alive;
    g.red_team.nexus_alive = data.red_nexus_alive;

    g.minions = (data.minions || []).map(m => {
      const minion = new Minion(m.team, m.position, m.max_hp, m.ad, m.is_siege);
      minion.hp = m.hp; minion.alive = m.alive;
      return minion;
    });

    return g;
  }

  static _restoreChamp(data) {
    const c = new Champion(data.id, data.team, data.ai_difficulty);
    c.level = data.level; c.exp = data.exp; c.gold = data.gold;
    c.kills = data.kills; c.deaths = data.deaths; c.assists = data.assists;
    c.position = data.position; c.alive = data.alive;
    c.respawn_timer = data.respawn_timer; c.can_shop = data.can_shop;
    c.items = [...data.items]; c.hex_augments = [...data.hex_augments];
    c.recalc_stats();
    if (c.alive) {
      c.hp = c.max_hp; c.mana = c.max_mana;
    } else {
      c.hp = 0;
    }
    return c;
  }
}