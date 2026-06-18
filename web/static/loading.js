// 加载页逻辑
const TIPS = [
  '海克斯大乱斗采用五杀摇滚模式，进攻至死方休。',
  '棱彩海克斯在三级时即可选择——选择你的命运！',
  '死亡才能购买装备，复活后记得先逛逛商店。',
  '大炮在 26.10 版本中大幅减少了移动锁定。',
  '水晶被摧毁后会派出超级兵，加快推进节奏。',
  '草丛是唯一的天然隐蔽区，进草可躲避敌方视野。',
  '满级18级，但海克斯选择只在 3/7/11/15 级触发。',
  '数据由 Riot Data Dragon 提供支持，Riot 不参与本项目运营。',
  '推进塔需按顺序：外塔→内塔→水晶→门牙塔→基地。',
  '炮车小兵对塔有3倍伤害，每两波刷新一台。',
];

let progress = 0;
let tipIdx = 0;
let playerId = 'Yasuo';

async function init() {
  // 从URL读玩家选择
  const params = new URLSearchParams(location.search);
  playerId = params.get('champ') || 'Yasuo';
  // 加载数据
  await loadGameData();
  const player = ALL_CHAMPIONS.find(c => c.id === playerId);
  if (player) {
    document.getElementById('splash-container').style.backgroundImage = `url(${player.splash_url})`;
    document.getElementById('loading-title').textContent = `${player.name} · 加载中`;
  }
  startLoading();
}

function startLoading() {
  const bar = document.getElementById('progress-bar');
  const pct = document.getElementById('loading-percent');
  const tip = document.getElementById('loading-tip');
  tip.textContent = TIPS[0];

  const interval = setInterval(() => {
    progress += Math.random() * 3 + 1.5;
    if (progress > 100) progress = 100;
    bar.style.width = progress + '%';
    pct.textContent = Math.floor(progress) + '%';

    if (Math.random() < 0.2) {
      tipIdx = (tipIdx + 1) % TIPS.length;
      tip.textContent = TIPS[tipIdx];
    }

    if (progress >= 100) {
      clearInterval(interval);
      setTimeout(() => {
        // 把游戏状态保存到 sessionStorage
        sessionStorage.setItem('hexlolfun_params', location.search);
        window.location.href = 'game.html?' + location.search.substring(1);
      }, 600);
    }
  }, 200);
}

init();