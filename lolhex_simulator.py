'''
英雄联盟 海克斯大乱斗 5v5 文字版

地图布局（蓝方 → 红方）:
[0 蓝方基地] → [1 蓝方门牙塔] → [2 蓝方水晶] → [3 草丛] 
→ [4 蓝方内塔] → [5 草丛] → [6 蓝方外塔] 
→ [7 河道草丛1] [8 河道草丛2] 
→ [9 红方外塔] → [10 草丛] → [11 红方内塔] 
→ [12 草丛] → [13 红方水晶] → [14 红方门牙塔] → [15 红方基地]

规则：
- 中路单线，无野区
- 每回合 = 10游戏秒
- 死亡才能买装备
- 被动金币 1/秒，击杀 300，助攻 100
- 3/7/11/15级触发海克斯三选一
'''

import json
import random
import os
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# 地图常量
# ============================================================
(BL_NEXUS, BL_NEXUS_T, BL_INHIB, BL_INNER_BUSH,
 BL_INNER_T, BL_OUTER_BUSH, BL_OUTER_T, MID_BUSH1,
 MID_BUSH2, RD_OUTER_T, RD_OUTER_BUSH, RD_INNER_T,
 RD_INNER_BUSH, RD_INHIB, RD_NEXUS_T, RD_NEXUS) = range(16)

LANE_NAMES = [
    "蓝方基地", "蓝方门牙塔", "蓝方水晶", "蓝方内塔后草丛",
    "蓝方内塔", "蓝方外塔后草丛", "蓝方外塔", "河道草丛①",
    "河道草丛②", "红方外塔", "红方外塔前草丛", "红方内塔",
    "红方内塔后草丛", "红方水晶", "红方门牙塔", "红方基地",
]

BUSH_POSITIONS = {BL_INNER_BUSH, BL_OUTER_BUSH, MID_BUSH1, MID_BUSH2, RD_OUTER_BUSH, RD_INNER_BUSH}

BLUE_TOWER_POS = {BL_NEXUS_T, BL_INNER_T, BL_OUTER_T}
RED_TOWER_POS = {RD_OUTER_T, RD_INNER_T, RD_NEXUS_T}
ALL_TOWER_POS = BLUE_TOWER_POS | RED_TOWER_POS

BLUE_BASE_POS = {BL_NEXUS, BL_NEXUS_T, BL_INHIB}
RED_BASE_POS = {RD_NEXUS, RD_NEXUS_T, RD_INHIB}

# 海克斯选择等级
HEX_LEVELS = [3, 7, 11, 15]

# 回合时长（游戏秒）
ROUND_DURATION = 10

# 小兵出波频率（回合数）
MINION_WAVE_INTERVAL = 3
# 小兵每回合移动格数
MINION_SPEED = 1
# 小兵战斗随机波动（±百分比），打破对称僵局
MINION_COMBAT_RANDOM = 0.3

# 经验常量
XP_PER_KILL_ASSIST = 50
XP_PASSIVE_PER_ROUND = 5
LEVEL_CAP = 18

# 推塔顺序：必须按顺序摧毁
# 蓝方: 外塔(6) → 内塔(4) → 水晶(2) → 门牙塔(1) → 基地(0)
# 红方: 外塔(9) → 内塔(11) → 水晶(13) → 门牙塔(14) → 基地(15)
BLUE_TOWER_ORDER = [BL_OUTER_T, BL_INNER_T, BL_INHIB, BL_NEXUS_T, BL_NEXUS]
RED_TOWER_ORDER = [RD_OUTER_T, RD_INNER_T, RD_INHIB, RD_NEXUS_T, RD_NEXUS]

# 推塔前置条件
TOWER_PREREQUISITE = {
    BL_OUTER_T: None,           # 外塔无条件
    BL_INNER_T: BL_OUTER_T,     # 内塔需要外塔倒
    BL_INHIB: BL_INNER_T,       # 水晶需要内塔倒
    BL_NEXUS_T: BL_INHIB,       # 门牙塔需要水晶倒
    BL_NEXUS: BL_NEXUS_T,       # 基地需要门牙塔倒
    RD_OUTER_T: None,
    RD_INNER_T: RD_OUTER_T,
    RD_INHIB: RD_INNER_T,
    RD_NEXUS_T: RD_INHIB,
    RD_NEXUS: RD_NEXUS_T,
}

# ============================================================
# 海克斯数据（从hex1.md提取）
# ============================================================
HEX_DATA = {
    '棱彩': [
        '亮出你的剑', '歌利亚巨人', '科学狂人', '玻璃大炮',
        '地狱三头犬', '夺金', '利刃华尔兹', '轨道镭射',
        '炼狱导管', '慢炖', '双刀流', '连拨击锤',
        '秘术冲拳', '战争交响乐', '砍伤', '珠光护手',
        '终极刷新', '终极唤醒', '最终形态', '你摸不到',
        '精怪魔法', '回归基本功', '尤里卡', '最万用的瞄准镜',
        '精准奇才', '巨人杀手', '全凭身法', '大地苏醒',
        '感受燃烧', '巨像的勇气', '死亡之环', '风语者的祝福',
        '蛋□□奶昔', '小猫咪找妈妈', '激光治疗', '米凯尔的祝福',
        '物法皆修', '踢踏舞', '尊我为王', '不详契约',
        '残忍', '任务：海牛阿福的勇士', '任务：沃格勒特的巫师帽',
        '史上最大雪球', '至高天诺言', '量子计算', '小丑学院',
        '全能龙魂', '质变：混沌', '潘多拉的盒子',
    ],
    '黄金': [
        '有始有终', '裁决使', '闪电打击', '心灵净化',
        '穿针引线', '夜狩', '火上浇油', '圣火',
        '魔鬼之舞', '罪恶快感', '炽烈黎明', '一板一眼',
        '接二连三', '暴击律动', '神射法师', '基石法师',
        '虚幻武器', '魔法飞弹', '古式佳酿', '溢流',
        '杀戮时间到了', '循环往复',
        '面包和黄油', '面包和果酱', '面包和奶酪',
        '更万用的瞄准镜', '老练狙神',
        '闪现向前', '狂徒豪气', '急急小子',
        '坦克引擎', '星界躯体', '黎明使者的坚决',
        '坚韧', '缩小射线', '超强大脑',
        '不动如山', '会心治疗', '全心为你',
        '无休回复', '灵魂虹吸', '吸血习性',
        '升级：狂妄', '升级：无尽之刃', '升级：耀光',
        '易损', '任务：钢化你心', '尖端发明家',
        '仆从大师', '作弊：我能回城！',
        '升级：雪球', '雪球扭蛋机',
        '回力OK镖', '神圣干预', '关键暴击', '质变：棱彩阶',
    ],
    '白银': [
        '大力', '残暴之力', '灵巧', '巫师式思考',
        '强力护盾', '唯快不破', '旋转至胜',
        '炼狱龙魂', '自我毁灭', '俯冲轰炸',
        '折磨者', '重量级打手', '台风', '活力再生',
    ],
}

# ============================================================
# 装备数据（从equipments.md提取关键装备）
# ============================================================
EQUIPMENT_LIST = [
    # (name, price, category, stats_dict)
    # ---- 出门装 ----
    ('多兰之刃', 475, '基础', {'ad': 10, 'hp': 100}),
    ('多兰之戒', 475, '基础', {'ap': 15, 'hp': 100}),
    ('多兰之盾', 475, '基础', {'hp': 120, 'armor': 10}),
    ('多兰之弓', 475, '基础', {'ad': 6, 'attack_speed': 0.12}),
    ('多兰之盔', 475, '基础', {'hp': 140}),
    ('长剑', 350, '基础', {'ad': 10}),
    ('短剑', 300, '基础', {'attack_speed': 0.12}),
    ('增幅典籍', 400, '基础', {'ap': 20}),
    ('红水晶', 350, '基础', {'hp': 150}),
    ('布甲', 300, '基础', {'armor': 15}),
    ('抗魔斗篷', 400, '基础', {'mr': 20}),
    ('吸血鬼权杖', 900, '基础', {}),  # 10%生命偷取（简化）
    # ---- AD装备 ----
    ('暴风之剑', 1650, 'AD', {'ad': 45}),
    ('无尽之刃', 3500, 'AD', {'ad': 70, 'crit': 0.25}),
    ('饮血剑', 3400, 'AD', {'ad': 55}),
    ('黑色切割者', 3000, 'AD', {'ad': 40, 'hp': 400}),
    ('守护天使', 3200, 'AD', {'ad': 40, 'armor': 40}),
    ('破败王者之刃', 3200, 'AD', {'ad': 40, 'attack_speed': 0.25}),
    ('收集者', 3000, 'AD', {'ad': 50, 'crit': 0.25}),
    # ---- AP装备 ----
    ('灭世者死亡之帽', 3500, 'AP', {'ap': 120}),
    ('中娅沙漏', 3250, 'AP', {'ap': 80, 'armor': 45}),
    ('虚空之杖', 3000, 'AP', {'ap': 80}),
    ('兰德里的折磨', 3000, 'AP', {'ap': 70, 'hp': 300}),
    ('卢登的回声', 2750, 'AP', {'ap': 90}),
    ('时光之杖', 2600, 'AP', {'hp': 400, 'ap': 60}),
    # ---- 坦克装备 ----
    ('狂徒铠甲', 3100, '坦克', {'hp': 800}),
    ('兰顿之兆', 2700, '坦克', {'hp': 350, 'armor': 60}),
    ('振奋盔甲', 2700, '坦克', {'hp': 400, 'mr': 55}),
    ('荆棘之甲', 2700, '坦克', {'armor': 70}),
    ('冰霜之心', 2500, '坦克', {'armor': 80}),
    ('日炎圣盾', 2700, '坦克', {'hp': 450, 'armor': 35}),
    # ---- 鞋子 ----
    ('狂战士胫甲', 1100, '鞋子', {'attack_speed': 0.35}),
    ('铁板靴', 1200, '鞋子', {'armor': 20}),
    ('水银之靴', 1100, '鞋子', {'mr': 30}),
    ('法师之靴', 1100, '鞋子', {}),  # 18法穿
]
# 按类别分组
EQUIP_BY_CATEGORY = {}
for eq in EQUIPMENT_LIST:
    name, price, cat, stats = eq
    EQUIP_BY_CATEGORY.setdefault(cat, []).append(eq)

# 基础移速 → 每回合移动格数
def ms_to_move(ms: int) -> int:
    """移速转每回合移动格子数。基础330移速=1格，每多30移速+0.1格，最低1格。"""
    return max(1, round(ms / 300, 1))


# ============================================================
# 加载英雄数据
# ============================================================
def load_champions():
    path = os.path.join(os.path.dirname(__file__), 'docs', 'heroes', '_all_champions.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['champions']


ALL_CHAMPIONS = load_champions()


# ============================================================
# Champion 类
# ============================================================
@dataclass
class Champion:
    id: str
    name: str
    title: str
    tags: list
    passive: str
    spells: list
    level: int = 1
    exp: int = 0
    gold: int = 500
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    position: int = BL_OUTER_T  # 蓝方从外塔出发
    team: str = 'blue'
    alive: bool = True
    respawn_timer: int = 0  # 剩余复活秒数

    # 实时战斗属性（基础值+成长+装备+海克斯）
    hp: int = 0
    max_hp: int = 0
    mana: int = 0
    max_mana: int = 0
    ad: float = 0
    ap: float = 0
    armor: float = 0
    mr: float = 0
    attack_speed: float = 0
    move_speed: int = 0
    crit: float = 0
    attack_range: int = 0

    # 基础值（用于重新计算）
    base_hp: int = 0
    base_hp_per_level: int = 0
    base_mp: int = 0
    base_mp_per_level: int = 0
    base_ad: float = 0
    base_ad_per_level: float = 0
    base_armor: float = 0
    base_armor_per_level: float = 0
    base_mr: float = 0
    base_mr_per_level: float = 0
    base_as: float = 0  # 基础攻速
    base_as_per_level: float = 0
    base_ms: int = 0
    base_crit: float = 0
    base_attack_range: int = 0

    items: list = field(default_factory=list)
    hex_augments: list = field(default_factory=list)

    # AI 相关
    ai_difficulty: str = ''  # ''=玩家控制, 'easy','medium','hard','expert'
    target_id: Optional[str] = None  # 当前目标

    # 技能冷却（简化版：每一回合只能用一个技能）
    skill_cooldowns: dict = field(default_factory=dict)

    # 商店锁（死亡才能买）
    can_shop: bool = False

    def __post_init__(self):
        if self.hp == 0:
            self.init_from_data()
        else:
            self.hp = max(0, self.hp)

    def init_from_data(self):
        if self.id not in ALL_CHAMPIONS:
            return
        d = ALL_CHAMPIONS[self.id]
        s = d['stats']
        self.base_hp = s['hp']
        self.base_hp_per_level = s['hpPerLevel']
        self.base_mp = s.get('mp', 0)
        self.base_mp_per_level = s.get('mpPerLevel', 0)
        self.base_ad = s['attackdamage']
        self.base_ad_per_level = s.get('attackdamagePerLevel', 0)
        self.base_armor = s['armor']
        self.base_armor_per_level = s['armorPerLevel']
        self.base_mr = s['spellblock']
        self.base_mr_per_level = s['spellblockPerLevel']
        self.base_as = s['attackspeed']
        self.base_as_per_level = s.get('attackspeedPerLevel', 2.5)
        self.base_ms = s['movespeed']
        self.base_crit = s.get('crit', 0)
        self.base_attack_range = s.get('attackrange', 175)
        self.recalc_stats()

    def recalc_stats(self):
        """根据等级+装备+海克斯重新计算属性"""
        lv = self.level
        self.max_hp = self.base_hp + self.base_hp_per_level * (lv - 1)
        self.max_mana = self.base_mp + self.base_mp_per_level * (lv - 1)
        self.ad = self.base_ad + self.base_ad_per_level * (lv - 1)
        self.ap = 0
        self.armor = self.base_armor + self.base_armor_per_level * (lv - 1)
        self.mr = self.base_mr + self.base_mr_per_level * (lv - 1)
        self.attack_speed = self.base_as + self.base_as_per_level / 100 * (lv - 1)
        self.move_speed = self.base_ms
        self.crit = self.base_crit
        self.attack_range = self.base_attack_range

        # 应用装备加成（简化：只加面板）
        for item in self.items:
            self._apply_item(item)

        # 海克斯效果暂不实现具体逻辑，先占位
        for aug in self.hex_augments:
            pass  # 后续实现各海克斯效果

        # 确保HP不超上限
        self.hp = min(self.hp, self.max_hp) if self.hp > 0 else self.max_hp
        self.mana = min(self.mana, self.max_mana) if self.mana > 0 else self.max_mana

    def _apply_item(self, item_name: str):
        """从EQUIPMENT_LIST查找装备属性并应用"""
        for eq in EQUIPMENT_LIST:
            if eq[0] == item_name:
                bonus = eq[3]
                self.ad += bonus.get('ad', 0)
                self.ap += bonus.get('ap', 0)
                self.max_hp += bonus.get('hp', 0)
                self.armor += bonus.get('armor', 0)
                self.mr += bonus.get('mr', 0)
                self.attack_speed += bonus.get('attack_speed', 0)
                self.crit += bonus.get('crit', 0)
                return
        # 未找到则静默跳过

    def gain_exp(self, amount: int):
        """获得经验，检查是否升级。返回(old_level, new_level)"""
        old_level = self.level
        self.exp += amount
        while self.level < LEVEL_CAP:
            exp_needed = 100 + self.level * 50
            if self.exp >= exp_needed:
                self.exp -= exp_needed
                self.level += 1
                self.recalc_stats()
                if self.alive:
                    self.hp = self.max_hp
            else:
                break
        return old_level, self.level

    def get_attack_range_in_positions(self) -> int:
        """攻击距离 → 位置格子数。近战=1，远程=2"""
        if self.attack_range <= 200:
            return 1
        elif self.attack_range <= 500:
            return 2
        else:
            return 3

    def get_name_display(self) -> str:
        return f"{self.name}({self.title})"

    def get_position_name(self) -> str:
        return f"{'🔵' if self.team == 'blue' else '🔴'} {LANE_NAMES[self.position]}" if self.alive else f"{self.get_name_display()} [阵亡]"


# ============================================================
# 建筑类
# ============================================================
@dataclass
class Tower:
    position: int
    team: str
    level: int = 1  # 外塔=1, 内塔=2, 门牙塔=3
    alive: bool = True
    hp: int = 2500
    max_hp: int = 2500
    armor: int = 60  # 塔的护甲（真实LOL约60）

    def __post_init__(self):
        tower_hp = {1: 2000, 2: 2500, 3: 3000}
        tower_ad = {1: 180, 2: 210, 3: 250}
        tower_armor = {1: 60, 2: 60, 3: 80}
        self.max_hp = tower_hp.get(self.level, 2000)
        self.hp = self.max_hp
        self.attack_damage = tower_ad.get(self.level, 180)
        self.armor = tower_armor.get(self.level, 60)

    def get_name(self):
        prefix = '蓝方' if self.team == 'blue' else '红方'
        names = {1: '外塔', 2: '内塔', 3: '门牙塔'}
        return f"{prefix}{names.get(self.level, '防御塔')}"

    def get_attack_range(self) -> int:
        """防御塔的攻击范围（位置格数）"""
        return 2


@dataclass
class Inhibitor:
    position: int
    team: str
    alive: bool = True
    hp: int = 4000
    max_hp: int = 4000
    respawn_timer: int = 0

    def get_name(self):
        prefix = '蓝方' if self.team == 'blue' else '红方'
        return f"{prefix}水晶"


# ============================================================
# 小兵类
# ============================================================
@dataclass
class Minion:
    team: str
    position: int
    hp: int = 300
    max_hp: int = 300
    ad: int = 15
    alive: bool = True
    is_siege: bool = False  # 炮车

    def get_name(self):
        prefix = '蓝方' if self.team == 'blue' else '红方'
        return f"{prefix}{'炮车' if self.is_siege else '小兵'}"


# ============================================================
# 队伍类
# ============================================================
@dataclass
class Team:
    side: str  # 'blue' or 'red'
    champions: list = field(default_factory=list)
    towers: dict = field(default_factory=dict)  # position -> Tower
    inhibitor: Optional[Inhibitor] = None
    nexus_alive: bool = True

    def get_alive_champions(self):
        return [c for c in self.champions if c.alive]

    def get_position_map(self):
        """{position: [champions]}"""
        m = {}
        for c in self.champions:
            if c.alive:
                m.setdefault(c.position, []).append(c)
        return m


# ============================================================
# 游戏主类
# ============================================================
class Game:
    def __init__(self, player_champion_id: str = 'Yasuo',
                 ally_ai_difficulty: str = 'medium',
                 enemy_ai_difficulty: str = 'medium'):
        self.game_time = 0  # 游戏秒数
        self.round_count = 0
        self.hex_level_order = ['棱彩', '黄金', '白银', '棱彩']  # 3/7/11/15级固定顺序
        self.hex_index = 0

        # 玩家
        self.player = self._create_champion(player_champion_id, 'blue', '')
        # 友方AI
        ally_ids = ['Garen', 'Lux', 'MasterYi', 'Annie']  # 临时选4个友方
        self.ally_ai = [
            self._create_champion(aid, 'blue', ally_ai_difficulty)
            for aid in ally_ids
        ]
        # 敌方AI
        enemy_ids = ['Darius', 'Ahri', 'Zed', 'Jinx', 'Leona']
        self.enemy_ai = [
            self._create_champion(eid, 'red', enemy_ai_difficulty)
            for eid in enemy_ids
        ]

        self.blue_team = Team('blue', [self.player] + self.ally_ai)
        self.red_team = Team('red', self.enemy_ai)

        # 初始化防御塔
        for pos in BLUE_TOWER_POS:
            lv = 1 if pos == BL_OUTER_T else (2 if pos == BL_INNER_T else 3)
            self.blue_team.towers[pos] = Tower(pos, 'blue', lv)
        for pos in RED_TOWER_POS:
            lv = 1 if pos == RD_OUTER_T else (2 if pos == RD_INNER_T else 3)
            self.red_team.towers[pos] = Tower(pos, 'red', lv)

        # 水晶
        self.blue_team.inhibitor = Inhibitor(BL_INHIB, 'blue')
        self.red_team.inhibitor = Inhibitor(RD_INHIB, 'red')

        # 红方英雄从红方外塔出发
        for c in self.enemy_ai:
            c.position = RD_OUTER_T

        self.game_over = False
        self.winner = None
        self.action_log = []
        self.minions: list = []  # 所有存活小兵
        self.minion_wave_counter = 0

    def _create_champion(self, champion_id: str, team: str, ai_diff: str) -> Champion:
        if champion_id not in ALL_CHAMPIONS:
            champion_id = 'Yasuo'
        data = ALL_CHAMPIONS[champion_id]
        c = Champion(
            id=champion_id,
            name=data['name'],
            title=data['title'],
            tags=data['tags'],
            passive=data['passive'],
            spells=data['spells'],
            team=team,
            ai_difficulty=ai_diff,
        )
        # 根据队伍设置初始位置
        if team == 'blue':
            c.position = BL_OUTER_T
        else:
            c.position = RD_OUTER_T
        return c

    def log(self, msg: str):
        self.action_log.append(msg)

    def get_team(self, side: str) -> Team:
        return self.blue_team if side == 'blue' else self.red_team

    def get_enemy_team(self, side: str) -> Team:
        return self.red_team if side == 'blue' else self.blue_team

    def get_all_champions(self) -> list:
        return [self.player] + self.ally_ai + self.enemy_ai

    def get_champion_at_position(self, pos: int, team: str) -> list:
        """获取某位置某方的存活英雄"""
        team_obj = self.get_team(team)
        return [c for c in team_obj.champions if c.alive and c.position == pos]

    def get_all_alive_at_position(self, pos: int) -> list:
        return [c for c in self.get_all_champions() if c.alive and c.position == pos]

    # ----- 回合结算 -----
    def process_round(self, player_action: str = ''):
        """处理一个回合"""
        self.action_log = []
        self.round_count += 1

        # 1. 处理玩家指令
        self._process_player_action(player_action)

        # 2. AI决策
        self._process_ai_decisions()

        # 3. 小兵生成
        self._spawn_minions()

        # 4. 小兵移动
        self._process_minion_movement()

        # 5. 战斗阶段（英雄 vs 英雄）
        self._process_combat()

        # 6. 小兵战斗（小兵 vs 小兵 + 小兵 vs 塔）
        self._process_minion_combat()

        # 7. 英雄攻击防御塔
        self._process_champions_attack_towers()

        # 8. 塔攻击（优先打小兵）
        self._process_tower_attacks()

        # 9. 死亡检查 + 经验金币
        self._process_deaths()

        # 10. 建筑摧毁检查
        self._check_structure_destruction()

        # 11. 推进时间
        self.game_time += ROUND_DURATION

        # 12. 被动金币 + 复活计时
        self._process_passive_gold()

        # 13. 被动经验 + 升级检查
        self._process_passive_exp()

        # 14. 海克斯触发检查
        self._process_level_up_hex()

        # 15. 胜负检查
        self._check_win_condition()

    def _process_player_action(self, action: str):
        """解析玩家指令"""
        if not action:
            return
        c = self.player
        if not c.alive:
            self.log(f"⏳ 你已阵亡，{c.respawn_timer}秒后复活")
            return

        parts = action.strip().lower().split()
        cmd = parts[0] if parts else ''

        if cmd == 'w' or cmd == '前进':
            # 前进
            move = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            new_pos = min(RD_NEXUS, c.position + move)
            self.log(f"▶ {c.get_name_display()} 前进了{move}格 → {LANE_NAMES[new_pos]}")
            c.position = new_pos

        elif cmd == 's' or cmd == '后退':
            move = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            new_pos = max(BL_NEXUS, c.position - move)
            self.log(f"◀ {c.get_name_display()} 后退了{move}格 → {LANE_NAMES[new_pos]}")
            c.position = new_pos

        elif cmd == 'a' or cmd == '攻击':
            target = parts[1] if len(parts) > 1 else ''
            self.log(f"⚔ {c.get_name_display()} 将攻击目标设为 {target}")

        elif cmd == 'b' or cmd == '回城':
            if c.team == 'blue':
                c.position = BL_NEXUS
            else:
                c.position = RD_NEXUS
            self.log(f"🏠 {c.get_name_display()} 回城")

        elif cmd == 'shop' or cmd == '商店':
            if c.can_shop:
                self.log(f"🏪 打开了商店")
            else:
                self.log(f"❌ 只有阵亡时才能打开商店")

        elif cmd == '蹲草':
            if c.position in BUSH_POSITIONS:
                self.log(f"🌿 {c.get_name_display()} 进入草丛隐蔽")
            else:
                self.log(f"❌ 当前位置没有草丛")

        elif cmd == '待命':
            self.log(f"⏸ {c.get_name_display()} 原地待命")

    def _process_ai_decisions(self):
        """AI决策：移动向最近敌人"""
        for c in self.get_all_champions():
            if not c.alive or c.ai_difficulty == '':
                continue
            # 简单AI：向前走
            if c.ai_difficulty == 'easy':
                self._ai_move_forward(c)
            elif c.ai_difficulty == 'medium':
                self._ai_medium(c)
            elif c.ai_difficulty == 'hard':
                self._ai_hard(c)
            elif c.ai_difficulty == 'expert':
                self._ai_expert(c)

    def _find_nearest_enemy(self, c: Champion) -> Optional[Champion]:
        """找最近的敌方存活英雄"""
        enemy_team = self.get_enemy_team(c.team)
        nearest = None
        min_dist = 999
        for ec in enemy_team.champions:
            if not ec.alive:
                continue
            dist = abs(c.position - ec.position)
            if dist < min_dist:
                min_dist = dist
                nearest = ec
        return nearest

    def _ai_move_forward(self, c: Champion):
        """简单AI：一直向前走"""
        if c.team == 'blue':
            if c.position < RD_NEXUS:
                c.position += 1
        else:
            if c.position > BL_NEXUS:
                c.position -= 1

    def _ai_medium(self, c: Champion):
        """中等AI：向最近敌人移动，在射程内攻击"""
        enemy = self._find_nearest_enemy(c)
        if not enemy:
            return
        dist = abs(c.position - enemy.position)
        atk_range = c.get_attack_range_in_positions()
        if dist > atk_range:
            step = 1 if c.team == 'blue' else -1
            new_pos = c.position + step
            # 不进敌方塔范围
            enemy_towers = RED_TOWER_POS if c.team == 'blue' else BLUE_TOWER_POS
            if new_pos in enemy_towers:
                return
            c.position = new_pos
            c.target_id = enemy.id

    def _ai_hard(self, c: Champion):
        """困难AI：会集火脆皮，但也会避塔"""
        if c.hp < c.max_hp * 0.3:
            # 残血时后撤
            step = -1 if c.team == 'blue' else 1
            c.position += step
            return
        enemy_team = self.get_enemy_team(c.team)
        # 找血量最低的
        lowest = None
        lowest_hp = 99999
        for ec in enemy_team.champions:
            if not ec.alive:
                continue
            if ec.hp < lowest_hp:
                lowest_hp = ec.hp
                lowest = ec
        if lowest:
            dist = abs(c.position - lowest.position)
            atk_range = c.get_attack_range_in_positions()
            if dist > atk_range:
                step = 1 if c.team == 'blue' else -1
                new_pos = c.position + step
                enemy_towers = RED_TOWER_POS if c.team == 'blue' else BLUE_TOWER_POS
                if new_pos in enemy_towers:
                    return
                c.position += step
            c.target_id = lowest.id

    def _ai_expert(self, c: Champion):
        """专家AI：会拉扯，残血会后退，会绕草丛"""
        if c.hp < c.max_hp * 0.35:
            step = -1 if c.team == 'blue' else 1
            new_pos = c.position + step
            # 退到草丛就停
            if new_pos in BUSH_POSITIONS:
                c.position = new_pos
            else:
                c.position += step
            self.log(f"🧠 {c.get_name_display()} 残血后撤到 {LANE_NAMES[c.position]}")
            return
        self._ai_hard(c)

    def _process_movement(self):
        """移动阶段 - 小兵移动已独立处理"""
        pass

    def _spawn_minions(self):
        """每3回合生成一波小兵"""
        self.minion_wave_counter += 1
        if self.minion_wave_counter < MINION_WAVE_INTERVAL:
            return
        self.minion_wave_counter = 0

        wave_num = self.round_count // MINION_WAVE_INTERVAL
        has_siege = wave_num > 0 and wave_num % 2 == 0  # 每2波出一台炮车

        # 蓝方小兵从蓝方基地(0)出发
        for _ in range(4):  # 4个近战兵
            self.minions.append(Minion(team='blue', position=BL_NEXUS, hp=350, max_hp=350, ad=18))
        for _ in range(3):  # 3个远程兵
            self.minions.append(Minion(team='blue', position=BL_NEXUS, hp=220, max_hp=220, ad=28))
        if has_siege:
            self.minions.append(Minion(team='blue', position=BL_NEXUS, hp=900, max_hp=900, ad=50, is_siege=True))

        # 红方小兵从红方基地(15)出发
        for _ in range(4):
            self.minions.append(Minion(team='red', position=RD_NEXUS, hp=350, max_hp=350, ad=18))
        for _ in range(3):
            self.minions.append(Minion(team='red', position=RD_NEXUS, hp=220, max_hp=220, ad=28))
        if has_siege:
            self.minions.append(Minion(team='red', position=RD_NEXUS, hp=900, max_hp=900, ad=50, is_siege=True))

        total = 8 if has_siege else 7
        self.log(f"⚔ 双方各派出{total}名小兵")

    def _process_minion_movement(self):
        """小兵移动：前方有敌方小兵则停止交战，无则前进"""
        # 构建快速查找集合：所有存活小兵的位置
        blue_minion_positions = {m.position for m in self.minions if m.alive and m.team == 'blue'}
        red_minion_positions = {m.position for m in self.minions if m.alive and m.team == 'red'}
        
        for m in self.minions[:]:
            if not m.alive:
                continue
            if m.team == 'blue':
                next_pos = m.position + 1
                if next_pos > RD_NEXUS:
                    continue
                # 前方位置有红方小兵 → 停止前进（交战）
                if next_pos in red_minion_positions:
                    continue
                # 当前位置有红方小兵 → 停火交战（不前进）
                if m.position in red_minion_positions:
                    continue
                m.position = next_pos
            else:
                next_pos = m.position - 1
                if next_pos < BL_NEXUS:
                    continue
                if next_pos in blue_minion_positions:
                    continue
                if m.position in blue_minion_positions:
                    continue
                m.position = next_pos

    def _process_minion_combat(self):
        """小兵战斗：同位置+相邻位置的敌对兵群体作战"""
        # 收集所有存活小兵
        alive_minions = [m for m in self.minions if m.alive]
        blue_minions = [m for m in alive_minions if m.team == 'blue']
        red_minions = [m for m in alive_minions if m.team == 'red']

        # ---- 1. 小兵 vs 小兵 ----
        # 检查每对敌对兵是否同位置或相邻
        blue_front = {}  # position -> list of blue minions
        red_front = {}   # position -> list of red minions
        for m in blue_minions:
            blue_front.setdefault(m.position, []).append(m)
        for m in red_minions:
            red_front.setdefault(m.position, []).append(m)

        # 把所有交火的前线位置找出来（同位置 or 相邻位置距离1）
        battle_positions = set()  # (pos_a, pos_b) where a is blue side, b is red side
        for bp in blue_front:
            for rp in red_front:
                dist = abs(bp - rp)
                if dist <= 1:  # 同位置或相邻位置
                    battle_positions.add((bp, rp))

        # 按位置组战斗 — 集火机制（先集火血量最低的敌人，形成滚雪球）
        for bp, rp in battle_positions:
            blue_group = blue_front.get(bp, [])
            red_group = red_front.get(rp, [])
            if not blue_group or not red_group:
                continue

            blue_total_ad = sum(m.ad for m in blue_group)
            red_total_ad = sum(m.ad for m in red_group)

            # 随机波动打破对称僵局（±30%）
            blue_ad_factor = 1.0 + random.uniform(-MINION_COMBAT_RANDOM, MINION_COMBAT_RANDOM)
            red_ad_factor = 1.0 + random.uniform(-MINION_COMBAT_RANDOM, MINION_COMBAT_RANDOM)
            blue_total_ad = int(blue_total_ad * blue_ad_factor)
            red_total_ad = int(red_total_ad * red_ad_factor)

            # 蓝方集火：按HP从低到高集火红方小兵
            remaining_dmg = blue_total_ad
            for m in sorted(red_group, key=lambda x: x.hp):
                if remaining_dmg <= 0 or not m.alive:
                    break
                dmg = min(remaining_dmg, m.hp)
                m.hp -= dmg
                remaining_dmg -= dmg
                if m.hp <= 0:
                    m.alive = False

            # 红方集火：按HP从低到高集火蓝方小兵
            remaining_dmg = red_total_ad
            for m in sorted(blue_group, key=lambda x: x.hp):
                if remaining_dmg <= 0 or not m.alive:
                    break
                dmg = min(remaining_dmg, m.hp)
                m.hp -= dmg
                remaining_dmg -= dmg
                if m.hp <= 0:
                    m.alive = False

        # ---- 2. 小兵攻击建筑（塔/水晶/基地） ----
        for m in alive_minions:
            if not m.alive:
                continue
            if m.team == 'blue':
                # 攻击红方防御塔
                if m.position in RED_TOWER_POS:
                    target_tower = self.red_team.towers.get(m.position)
                    if target_tower and target_tower.alive:
                        self._minion_attack_tower(m, target_tower)
                # 攻击红方水晶
                elif m.position == RD_INHIB and self.red_team.inhibitor and self.red_team.inhibitor.alive:
                    self._minion_attack_building(m, '红方水晶', self.red_team.inhibitor)
                # 攻击红方基地
                elif m.position == RD_NEXUS:
                    self._minion_attack_nexus(m, 'red')
            elif m.team == 'red':
                # 攻击蓝方防御塔
                if m.position in BLUE_TOWER_POS:
                    target_tower = self.blue_team.towers.get(m.position)
                    if target_tower and target_tower.alive:
                        self._minion_attack_tower(m, target_tower)
                # 攻击蓝方水晶
                elif m.position == BL_INHIB and self.blue_team.inhibitor and self.blue_team.inhibitor.alive:
                    self._minion_attack_building(m, '蓝方水晶', self.blue_team.inhibitor)
                # 攻击蓝方基地
                elif m.position == BL_NEXUS:
                    self._minion_attack_nexus(m, 'blue')

    def _minion_attack_tower(self, m: Minion, target_tower: Tower):
        """小兵攻击防御塔，检查前置塔条件"""
        prereq = TOWER_PREREQUISITE.get(target_tower.position)
        if prereq:
            team = self.blue_team if m.team == 'blue' else self.red_team
            prereq_tower = team.towers.get(prereq)
            if prereq_tower and prereq_tower.alive:
                return
        tower_armor = target_tower.armor
        dmg_mult = 100 / (100 + tower_armor)
        raw_dmg = m.ad
        # 炮车对塔3倍伤害
        if m.is_siege:
            raw_dmg *= 3
        dmg = max(1, int(raw_dmg * dmg_mult))
        target_tower.hp -= dmg
        tag = '🚌' if m.is_siege else '⚔'
        self.log(f"{tag} {m.get_name()} → {target_tower.get_name()} 造成{dmg}伤害 "
                 f"({target_tower.hp}/{target_tower.max_hp})")

    def _minion_attack_building(self, m: Minion, name: str, building):
        """小兵攻击水晶等建筑"""
        raw_dmg = m.ad
        if m.is_siege:
            raw_dmg *= 2
        dmg = max(1, int(raw_dmg))
        building.hp -= dmg
        if building.hp <= 0:
            building.alive = False
            self.log(f"💎 {name} 被摧毁！（小兵）")
        else:
            tag = '🚌' if m.is_siege else '⚔'
            self.log(f"{tag} {m.get_name()} → {name} 造成{dmg}伤害 ({building.hp}/{building.max_hp})")

    def _minion_attack_nexus(self, m: Minion, team: str):
        """小兵攻击基地"""
        if not hasattr(self, '_nexus_hp'):
            self._nexus_hp = {BL_NEXUS: 5000, RD_NEXUS: 5000}
        nexus_pos = RD_NEXUS if team == 'red' else BL_NEXUS
        team_obj = self.red_team if team == 'red' else self.blue_team
        if not team_obj.nexus_alive:
            return
        raw_dmg = m.ad
        if m.is_siege:
            raw_dmg *= 2
        dmg = max(1, int(raw_dmg))
        self._nexus_hp[nexus_pos] -= dmg
        if self._nexus_hp[nexus_pos] <= 0:
            team_obj.nexus_alive = False
            self.log(f"🔥 {team.upper()}方基地 被摧毁！（小兵）")
        else:
            tag = '🚌' if m.is_siege else '⚔'
            self.log(f"{tag} {m.get_name()} → {'红方' if team == 'red' else '蓝方'}基地 "
                     f"造成{dmg}伤害 ({self._nexus_hp[nexus_pos]}/5000)")

    def _process_champions_attack_towers(self):
        """英雄攻击建筑：与建筑在同一格且有攻击条件时"""
        all_champs = self.get_all_champions()
        for c in all_champs:
            if not c.alive:
                continue
            if c.team == 'blue':
                # 攻击红方防御塔
                if c.position in RED_TOWER_POS:
                    target_tower = self.red_team.towers.get(c.position)
                    if target_tower and target_tower.alive:
                        self._champion_attack_tower(c, target_tower)
                # 攻击红方水晶
                elif c.position == RD_INHIB and self.red_team.inhibitor and self.red_team.inhibitor.alive:
                    self._champion_attack_inhibitor(c, self.red_team.inhibitor, '红方水晶')
                # 攻击红方基地
                elif c.position == RD_NEXUS:
                    self._champion_attack_nexus(c, 'red')
            else:
                # 攻击蓝方防御塔
                if c.position in BLUE_TOWER_POS:
                    target_tower = self.blue_team.towers.get(c.position)
                    if target_tower and target_tower.alive:
                        self._champion_attack_tower(c, target_tower)
                # 攻击蓝方水晶
                elif c.position == BL_INHIB and self.blue_team.inhibitor and self.blue_team.inhibitor.alive:
                    self._champion_attack_inhibitor(c, self.blue_team.inhibitor, '蓝方水晶')
                # 攻击蓝方基地
                elif c.position == BL_NEXUS:
                    self._champion_attack_nexus(c, 'blue')

    def _champion_attack_tower(self, c: Champion, target_tower: Tower):
        """英雄攻击防御塔"""
        # 检查前置塔条件
        prereq = TOWER_PREREQUISITE.get(target_tower.position)
        if prereq:
            prereq_tower = self.red_team.towers.get(prereq) if c.team == 'blue' else self.blue_team.towers.get(prereq)
            if prereq_tower and prereq_tower.alive:
                return
        tower_armor = target_tower.armor
        dmg_mult = 100 / (100 + tower_armor)
        raw = c.ad * 0.8 + c.ap * 0.4
        dmg = max(10, int(raw * dmg_mult))
        target_tower.hp -= dmg
        self.log(f"🔨 {c.get_name_display()} → {target_tower.get_name()} 造成{dmg}伤害 "
                 f"({target_tower.hp}/{target_tower.max_hp})")

    def _champion_attack_inhibitor(self, c: Champion, inhib, name: str):
        """英雄攻击水晶"""
        dmg = max(10, int(c.ad * 0.6 + c.ap * 0.3))
        inhib.hp -= dmg
        self.log(f"🔨 {c.get_name_display()} → {name} 造成{dmg}伤害 ({inhib.hp}/{inhib.max_hp})")

    def _champion_attack_nexus(self, c: Champion, team: str):
        """英雄攻击基地"""
        if not hasattr(self, '_nexus_hp'):
            self._nexus_hp = {BL_NEXUS: 5000, RD_NEXUS: 5000}
        nexus_pos = RD_NEXUS if team == 'red' else BL_NEXUS
        team_obj = self.red_team if team == 'red' else self.blue_team
        if not team_obj.nexus_alive:
            return
        dmg = max(10, int(c.ad * 0.6 + c.ap * 0.3))
        self._nexus_hp[nexus_pos] -= dmg
        if self._nexus_hp[nexus_pos] <= 0:
            team_obj.nexus_alive = False
            self.log(f"🔥 {team.upper()}方基地 被摧毁！（英雄）")
        else:
            self.log(f"🔨 {c.get_name_display()} → {'红方' if team == 'red' else '蓝方'}基地 "
                     f"造成{dmg}伤害 ({self._nexus_hp[nexus_pos]}/5000)")

    def _process_combat(self):
        """战斗阶段：英雄攻击英雄 + 英雄攻击小兵"""
        all_champs = self.get_all_champions()
        # 英雄vs英雄（双向攻击去重）
        attack_pairs = set()

        for c in all_champs:
            if not c.alive:
                continue
            atk_range = c.get_attack_range_in_positions()
            # 找所有在攻击范围内的敌方英雄
            enemy_team = self.get_enemy_team(c.team)
            for ec in enemy_team.champions:
                if not ec.alive:
                    continue
                dist = abs(c.position - ec.position)
                if dist <= atk_range:
                    pair = tuple(sorted([c.id, ec.id]))
                    if pair in attack_pairs:
                        continue
                    attack_pairs.add(pair)
                    self._resolve_attack(c, ec)

        # 英雄vs小兵：英雄自动攻击同位置或相邻位置的敌方小兵
        for c in all_champs:
            if not c.alive:
                continue
            atk_range = c.get_attack_range_in_positions()
            # 找射程内的敌方小兵
            target_minions = []
            for m in self.minions:
                if not m.alive or m.team == c.team:
                    continue
                dist = abs(c.position - m.position)
                if dist <= atk_range:
                    target_minions.append(m)
            if not target_minions:
                continue
            # 集火血量最低的小兵
            target = min(target_minions, key=lambda x: x.hp)
            dmg = max(1, int(c.ad))  # 小兵无护甲
            # 暴击
            if random.random() < c.crit:
                dmg = int(dmg * 1.75)
            target.hp -= dmg
            if target.hp <= 0:
                target.alive = False
            # 不记录每个小兵击杀日志，减少刷屏

    def _resolve_attack(self, attacker: Champion, defender: Champion):
        """结算一次攻击"""
        armor = defender.armor
        damage_mult = 100 / (100 + armor)
        raw_damage = attacker.ad
        damage = max(1, int(raw_damage * damage_mult))

        # 暴击
        if random.random() < attacker.crit:
            damage = int(damage * 1.75)
            crit_str = "暴击！"
        else:
            crit_str = ""

        defender.hp = max(0, defender.hp - damage)
        self.log(f"💥 {attacker.get_name_display()} → {defender.get_name_display()} {crit_str} 造成{damage}伤害 "
                 f"({defender.hp}/{defender.max_hp})")

    def _process_tower_attacks(self):
        """防御塔攻击：优先打小兵，没有小兵再打英雄"""
        for pos, tower in list(self.blue_team.towers.items()):
            if not tower.alive:
                continue
            # 找射程内的小兵
            target = None
            for m in self.minions:
                if m.alive and m.team == 'red' and abs(m.position - pos) <= tower.get_attack_range():
                    target = m
                    break
            # 没小兵就打英雄
            if not target:
                for ec in self.red_team.champions:
                    if ec.alive and abs(ec.position - pos) <= tower.get_attack_range():
                        target = ec
                        break
            if target:
                damage = tower.attack_damage
                if isinstance(target, Minion):
                    target.hp -= damage
                    if target.hp <= 0:
                        target.alive = False
                    self.log(f"🏛 {tower.get_name()} → {target.get_name()} 造成{damage}伤害")
                else:
                    target.hp = max(0, target.hp - damage)
                    self.log(f"🏛 {tower.get_name()} → {target.get_name_display()} 造成{damage}伤害 "
                             f"({target.hp}/{target.max_hp})")

        for pos, tower in list(self.red_team.towers.items()):
            if not tower.alive:
                continue
            target = None
            for m in self.minions:
                if m.alive and m.team == 'blue' and abs(m.position - pos) <= tower.get_attack_range():
                    target = m
                    break
            if not target:
                for bc in self.blue_team.champions:
                    if bc.alive and abs(bc.position - pos) <= tower.get_attack_range():
                        target = bc
                        break
            if target:
                damage = tower.attack_damage
                if isinstance(target, Minion):
                    target.hp -= damage
                    if target.hp <= 0:
                        target.alive = False
                    self.log(f"🏛 {tower.get_name()} → {target.get_name()} 造成{damage}伤害")
                else:
                    target.hp = max(0, target.hp - damage)
                    self.log(f"🏛 {tower.get_name()} → {target.get_name_display()} 造成{damage}伤害 "
                             f"({target.hp}/{target.max_hp})")

    def _process_deaths(self):
        """处理阵亡、经验金币分发。记录本回合阵亡名单"""
        self._died_this_round = set()
        all_champs = self.get_all_champions()
        for c in all_champs:
            if c.alive and c.hp <= 0:
                c.alive = False
                c.deaths += 1
                c.respawn_timer = c.level * 3
                c.can_shop = True
                self._died_this_round.add(c.id)
                self.log(f"💀 {c.get_name_display()} 阵亡！{c.respawn_timer}秒后复活")

                # XP: 附近队友每人获得经验
                for teammate in self.get_team(c.team).champions:
                    if teammate.alive:
                        if abs(teammate.position - c.position) <= 3:
                            old_lv, new_lv = teammate.gain_exp(XP_PER_KILL_ASSIST)
                            if new_lv > old_lv:
                                self.log(f"⬆ {teammate.get_name_display()} 升到{new_lv}级！")

                # 击杀金币（简化：最近敌人获得击杀）
                enemy_team = self.get_enemy_team(c.team)
                killer = None
                min_dist = 999
                for ec in enemy_team.champions:
                    if ec.alive:
                        dist = abs(ec.position - c.position)
                        if dist < min_dist:
                            min_dist = dist
                            killer = ec
                if killer:
                    killer.gold += 300
                    killer.kills += 1
                    # 击杀者也获得经验
                    killer.gain_exp(XP_PER_KILL_ASSIST)
                    self.log(f"💰 {killer.get_name_display()} 获得 300G 击杀奖励")
                    for teammate in self.get_team(killer.team).champions:
                        if teammate.alive and teammate.id != killer.id:
                            if abs(teammate.position - c.position) <= 2:
                                teammate.gold += 100
                                teammate.assists += 1

        # 清理死亡小兵
        self.minions = [m for m in self.minions if m.alive and m.hp > 0]

    def _process_passive_gold(self):
        """每回合被动金币 + 复活计时（本回合刚死的跳过计时）"""
        for c in self.get_all_champions():
            if c.alive:
                c.gold += ROUND_DURATION
            elif not c.alive and c.respawn_timer > 0:
                # 本回合刚死的跳过复活计时
                if c.id in getattr(self, '_died_this_round', set()):
                    continue
                c.respawn_timer -= ROUND_DURATION
                if c.respawn_timer <= 0:
                    c.alive = True
                    c.hp = c.max_hp
                    c.can_shop = False
                    c.position = BL_NEXUS if c.team == 'blue' else RD_NEXUS
                    self.log(f"✨ {c.get_name_display()} 复活！")

    def _process_level_up_hex(self):
        """检查海克斯选择事件：3/7/11/15级时触发
        - 玩家：设为待选状态，等待 UI 选择
        - AI：自动随机选择一个
        """
        for c in self.get_all_champions():
            if c.level not in HEX_LEVELS:
                continue
            expected_idx = HEX_LEVELS.index(c.level)
            # 过滤掉占位，统计实际已选的海克斯
            actual_augments = [a for a in c.hex_augments if a != '__pending__']
            if len(actual_augments) > expected_idx:
                continue  # 已经选过
            if '__pending__' in c.hex_augments:
                continue  # 正在等待选择，不要重复触发
            quality = self.hex_level_order[expected_idx]
            pool = HEX_DATA.get(quality, [])
            if not pool:
                continue
            options = random.sample(pool, min(3, len(pool)))

            if c.id == self.player.id:
                # 玩家：挂起等待选择
                self._pending_hex = {
                    'champion_id': c.id,
                    'quality': quality,
                    'options': options,
                    'level': c.level,
                }
                c.hex_augments.append('__pending__')
                self.log(f"🔮 你触发了海克斯选择！品质: {quality}")
                self.log(f"   选项: {' / '.join(options)}")
            else:
                # AI：自动随机选
                chosen = random.choice(options)
                c.hex_augments.append(chosen)
                c.recalc_stats()
                self.log(f"🔮 {c.get_name_display()} 获得海克斯 [{quality}]: {chosen}")

    def select_hex(self, champion_id: str, option_index: int) -> str:
        """玩家选择一个海克斯"""
        if not hasattr(self, '_pending_hex') or not self._pending_hex:
            return "❌ 当前没有待选择的海克斯"
        pending = self._pending_hex
        if pending['champion_id'] != champion_id:
            return "❌ 该英雄没有待选择的海克斯"
        if option_index < 0 or option_index >= len(pending['options']):
            return "❌ 无效选项"
        chosen = pending['options'][option_index]
        # 找到对应英雄，替换占位
        for c in self.get_all_champions():
            if c.id == champion_id:
                if c.hex_augments and c.hex_augments[-1] == '__pending__':
                    c.hex_augments[-1] = chosen
                else:
                    c.hex_augments.append(chosen)
                c.recalc_stats()
                self.log(f"✅ {c.get_name_display()} 获得海克斯: {chosen}")
                break
        self._pending_hex = None
        return f"✅ 获得海克斯: {chosen}"

    def _check_structure_destruction(self):
        """检查建筑摧毁（塔/水晶/基地已由小兵和英雄直接扣血，此方法仅做状态确认和日志）"""
        for team_key in ['blue_team', 'red_team']:
            team = getattr(self, team_key)
            # 防御塔摧毁检查
            for pos, tower in list(team.towers.items()):
                if tower.alive and tower.hp <= 0:
                    tower.alive = False
                    self.log(f"🏛 {tower.get_name()} 被摧毁！")

            # 水晶摧毁检查（水晶血量已由小兵/英雄直接扣除）
            inhib = team.inhibitor
            if inhib and inhib.alive and inhib.hp <= 0:
                inhib.alive = False
                self.log(f"💎 {inhib.get_name()} 被摧毁！")

            # 基地摧毁检查（基地血量已由小兵/英雄直接扣除）
            if team.nexus_alive:
                if not hasattr(self, '_nexus_hp'):
                    self._nexus_hp = {BL_NEXUS: 5000, RD_NEXUS: 5000}
                nexus_pos = BL_NEXUS if team.side == 'blue' else RD_NEXUS
                if self._nexus_hp.get(nexus_pos, 5000) <= 0:
                    team.nexus_alive = False
                    self.log(f"🔥 {team.side.upper()}方基地 被摧毁！")

    def _process_passive_exp(self):
        """每回合被动经验"""
        for c in self.get_all_champions():
            if c.alive and c.level < LEVEL_CAP:
                old_lv, new_lv = c.gain_exp(XP_PASSIVE_PER_ROUND)
                if new_lv > old_lv:
                    self.log(f"⬆ {c.get_name_display()} 升到{new_lv}级！")

    def _check_win_condition(self):
        """检查胜负"""
        if not self.blue_team.nexus_alive:
            self.game_over = True
            self.winner = 'red'
            self.log("💥 红方胜利！蓝方基地被摧毁！")
        elif not self.red_team.nexus_alive:
            self.game_over = True
            self.winner = 'blue'
            self.log("💥 蓝方胜利！红方基地被摧毁！")

    # ----- 显示 -----
    def get_map_display(self) -> str:
        """生成地图显示"""
        pos_units = {i: [] for i in range(16)}
        for c in self.get_all_champions():
            if c.alive:
                tag = 'P' if c.id == self.player.id else ('B' if c.team == 'blue' else 'R')
                pos_units[c.position].append(tag)
        # 小兵
        for m in self.minions:
            if m.alive:
                tag = 'b' if m.team == 'blue' else 'r'
                pos_units[m.position].append(tag)
        # 塔
        for p, t in self.blue_team.towers.items():
            if t.alive:
                hp_pct = t.hp / t.max_hp
                tag = '🛡' if hp_pct > 0.5 else ('⚔' if hp_pct > 0.25 else '💔')
                pos_units[p].append(tag)
        for p, t in self.red_team.towers.items():
            if t.alive:
                hp_pct = t.hp / t.max_hp
                tag = '🛡' if hp_pct > 0.5 else ('⚔' if hp_pct > 0.25 else '💔')
                pos_units[p].append(tag)

        # 生成地图字符串
        parts = []
        for i in range(16):
            units = ''.join(pos_units[i]) if pos_units[i] else '··'
            name_short = LANE_NAMES[i][-2:]
            if i in BUSH_POSITIONS:
                parts.append(f"[{units}]🌿")
            elif i in ALL_TOWER_POS:
                parts.append(f"[{units}]�")
            else:
                parts.append(f"[{units}]")
        return '—'.join(parts)

    def get_status_display(self) -> str:
        """生成状态面板"""
        time_min = self.game_time // 60
        time_sec = self.game_time % 60
        alive_minions = len([m for m in self.minions if m.alive])
        lines = [
            f"══════════════ 第{self.round_count}回合 ══════════════",
            f"游戏时间: {time_min}:{time_sec:02d}  小兵: {alive_minions}",
            "",
            f"📍 地图:",
            self.get_map_display(),
            "",
            f"👤 玩家: {self.player.get_name_display()}",
            f"   LV.{self.player.level} ❤{self.player.hp}/{self.player.max_hp} "
            f"🗡{self.player.ad:.0f} 🛡{self.player.armor:.0f} 💰{self.player.gold}G",
            f"   位置: {LANE_NAMES[self.player.position]}",
            f"   K/D/A: {self.player.kills}/{self.player.deaths}/{self.player.assists}",
        ]

        # 装备显示
        if self.player.items:
            lines.append(f"   🎒 {' '.join(self.player.items)}")
        # 海克斯显示
        hexes = [h for h in self.player.hex_augments if h != '__pending__']
        if hexes:
            lines.append(f"   🔮 {' | '.join(hexes)}")

        # 塔状态
        bt = []
        for p, t in sorted(self.blue_team.towers.items()):
            if t.alive:
                pct = t.hp / t.max_hp
                bar = '█' * int(pct * 5) + '░' * (5 - int(pct * 5))
                bt.append(f"{t.get_name()}[{bar}]")
        rt = []
        for p, t in sorted(self.red_team.towers.items()):
            if t.alive:
                pct = t.hp / t.max_hp
                bar = '█' * int(pct * 5) + '░' * (5 - int(pct * 5))
                rt.append(f"{t.get_name()}[{bar}]")
        lines.append(f"\n🏛 蓝方: {' '.join(bt)}")
        lines.append(f"🏛 红方: {' '.join(rt)}")

        # 友方状态
        alive_allies = [c for c in self.ally_ai if c.alive]
        if alive_allies:
            lines.append(f"\n🤝 友方:")
            for c in alive_allies:
                lines.append(f"   {c.get_name_display()} LV.{c.level} ❤{c.hp}/{c.max_hp} "
                             f"📍{LANE_NAMES[c.position]}")

        dead_allies = [c for c in self.ally_ai if not c.alive]
        if dead_allies:
            for c in dead_allies:
                lines.append(f"   💀 {c.get_name_display()} 复活中({max(0,c.respawn_timer)}s)")

        # 敌方状态
        alive_enemies = [c for c in self.enemy_ai if c.alive]
        if alive_enemies:
            lines.append(f"\n👹 敌方:")
            for c in alive_enemies:
                lines.append(f"   {c.get_name_display()} LV.{c.level} ❤{c.hp}/{c.max_hp} "
                             f"📍{LANE_NAMES[c.position]}")

        return '\n'.join(lines)

    def get_round_log(self) -> str:
        return '\n'.join(self.action_log) if self.action_log else "本回合无事发生"

    def is_player_dead(self) -> bool:
        return not self.player.alive

    def show_shop(self):
        """显示商店界面（死亡时可用）"""
        if not self.player.can_shop:
            return "❌ 只有阵亡时才能使用商店"

        lines = [f"══════════ 商店 ══════════", f"💰 当前金币: {self.player.gold}G", ""]
        idx = 1
        self._shop_item_map = {}  # idx -> (name, price)
        for cat_name in ['基础', 'AD', 'AP', '坦克', '鞋子']:
            items = EQUIP_BY_CATEGORY.get(cat_name, [])
            if not items:
                continue
            lines.append(f"── {cat_name} ──")
            for name, price, _, desc in items:
                owned = "✓" if name in self.player.items else ""
                self._shop_item_map[idx] = (name, price)
                lines.append(f"{idx}. {name} [{price}G] {owned}")
                idx += 1
            lines.append("")
        lines.append("输入 buy <序号> 购买")
        return '\n'.join(lines)

    def buy_item(self, idx: int) -> str:
        """购买商品"""
        if not self.player.can_shop:
            return "❌ 只有阵亡时才能购买"
        if not hasattr(self, '_shop_item_map') or not self._shop_item_map:
            return "❌ 请先打开商店查看"
        item_info = self._shop_item_map.get(idx)
        if not item_info:
            return "❌ 无效序号"
        name, price = item_info
        if self.player.gold < price:
            return f"❌ 金币不足！需要{price}G，你有{self.player.gold}G"
        self.player.gold -= price
        self.player.items.append(name)
        self.player.recalc_stats()
        return f"✅ 购买了 {name}！"

    def show_hex_selection(self) -> str:
        """显示海克斯选择界面"""
        if not hasattr(self, '_pending_hex') or not self._pending_hex:
            return "❌ 当前没有待选择的海克斯"
        p = self._pending_hex
        lines = [
            f"══════════ 海克斯选择 ══════════",
            f"品质: {p['quality']}  |  等级: {p['level']}",
            f"英雄: {p['champion_id']}",
            "",
        ]
        for i, opt in enumerate(p['options'], 1):
            lines.append(f"{i}. {opt}")
        lines.append("")
        lines.append("输入 hex <序号> 选择")
        return '\n'.join(lines)


# ============================================================
# 游戏主循环
# ============================================================
def play_game():
    print("=" * 40)
    print("  英雄联盟 · 海克斯大乱斗 文字版")
    print("=" * 40)
    print()

    # 选英雄
    champ_list = sorted(ALL_CHAMPIONS.keys())
    print(f"共有 {len(champ_list)} 个英雄可用")
    print("请输入英雄ID（如 Yasuo, Ahri, Garen...）:")
    choice = input("> ").strip()
    if choice not in ALL_CHAMPIONS:
        print(f"未找到 {choice}，使用默认英雄 Yasuo")
        choice = 'Yasuo'

    game = Game(player_champion_id=choice, ally_ai_difficulty='medium', enemy_ai_difficulty='medium')

    print(f"\n你选择了 {game.player.get_name_display()}")
    input("按 Enter 开始游戏...")

    # 游戏循环
    while not game.game_over:
        # 检查是否有待选择的海克斯
        has_pending_hex = hasattr(game, '_pending_hex') and game._pending_hex is not None

        # 显示状态
        print('\n' + game.get_status_display())
        print('\n' + '-' * 40)

        # 如果有待选海克斯，显示海克斯选择界面
        if has_pending_hex:
            print(game.show_hex_selection())

        # 如果玩家阵亡且没有待选海克斯，显示商店
        if game.is_player_dead() and not has_pending_hex:
            print(game.show_shop())

        # 显示上回合日志
        if game.action_log:
            print(f"\n📋 战报:")
            for line in game.action_log[-10:]:
                print(f"  {line}")

        # 回合操作提示
        print(f"\n🎮 指令:")
        print(f"  w [格数] - 前进    s [格数] - 后退")
        print(f"  a <目标> - 集火    b - 回城")
        print(f"  蹲草 - 进入草丛    待命 - 原地不动")
        if has_pending_hex:
            print(f"  hex <序号> - 选择海克斯")
        if game.is_player_dead() and not has_pending_hex:
            print(f"  shop - 打开商店    buy <序号> - 购买")
        print(f"  q - 退出游戏")

        cmd = input("\n> ").strip()
        if cmd.lower() == 'q':
            break

        # 海克斯选择
        if cmd.lower().startswith('hex') and has_pending_hex:
            parts = cmd.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                result = game.select_hex(game.player.id, idx)
                print(result)
            continue

        # 购买/商店
        if cmd.lower() == 'shop' and game.is_player_dead() and not has_pending_hex:
            print(game.show_shop())
            continue
        if cmd.lower().startswith('buy') and game.is_player_dead() and not has_pending_hex:
            parts = cmd.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1])
                result = game.buy_item(idx)
                print(result)
            continue

        # 结算本回合
        game.process_round(cmd)

    print("\n游戏结束！")


# ============================================================
# 主菜单
# ============================================================
def main():
    while True:
        print("\n" + "=" * 40)
        print("  英雄联盟 · 海克斯大乱斗 文字版")
        print("=" * 40)
        print("1. 开始游戏")
        print("2. 设置（海克斯版本）")
        print("3. 查看档案")
        print("4. 退出游戏")
        print("-" * 40)
        choice = input("请选择 > ").strip()

        if choice == '1':
            play_game()
        elif choice == '2':
            print("\n⚙ 设置 - 海克斯版本（待实现）")
            print("1. 海克斯1.0")
            print("2. 海克斯2.0")
            print("3. 海克斯3.0")
        elif choice == '3':
            print("\n📚 档案（待实现）")
        elif choice == '4':
            print("再见！")
            break
        else:
            print("无效选项")


if __name__ == '__main__':
    main()