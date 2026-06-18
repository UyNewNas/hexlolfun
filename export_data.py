'''
将Python游戏数据导出为静态JSON，供前端JS使用
运行：python export_data.py
生成：web/static/data/champions.json, hex.json, equipments.json
'''
import json
import os
import sys

sys.path.insert(0, '.')
from lolhex_simulator import ALL_CHAMPIONS, HEX_DATA, EQUIPMENT_LIST, EQUIP_BY_CATEGORY

OUT_DIR = 'web/static/data'
os.makedirs(OUT_DIR, exist_ok=True)

# 1. 英雄数据：精简版（只保留游戏需要的）
DDRAGON = "16.10.1"
DDRAGON_IMG = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON}/img"
DDRAGON_LOADING = f"https://ddragon.leagueoflegends.com/cdn/img/champion/loading"

champions_data = []
for cid, c in ALL_CHAMPIONS.items():
    s = c['stats']
    champions_data.append({
        'id': cid,
        'name': c['name'],
        'title': c['title'],
        'tags': c['tags'],
        'base_hp': s['hp'],
        'hp_per_level': s['hpPerLevel'],
        'base_mp': s.get('mp', 0),
        'mp_per_level': s.get('mpPerLevel', 0),
        'base_ad': s['attackdamage'],
        'ad_per_level': s.get('attackdamagePerLevel', 0),
        'base_armor': s['armor'],
        'armor_per_level': s['armorPerLevel'],
        'base_mr': s['spellblock'],
        'mr_per_level': s['spellblockPerLevel'],
        'base_as': s['attackspeed'],
        'as_per_level': s.get('attackspeedPerLevel', 2.5),
        'base_ms': s['movespeed'],
        'base_crit': s.get('crit', 0),
        'attack_range': s.get('attackrange', 175),
        'square_url': f"{DDRAGON_IMG}/champion/{cid}.png",
        'splash_url': f"{DDRAGON_LOADING}/{cid}_0.jpg",
    })

with open(f'{OUT_DIR}/champions.json', 'w', encoding='utf-8') as f:
    json.dump(champions_data, f, ensure_ascii=False, separators=(',', ':'))
print(f'✓ champions.json: {len(champions_data)}个英雄')

# 2. 海克斯数据
with open(f'{OUT_DIR}/hex.json', 'w', encoding='utf-8') as f:
    json.dump(HEX_DATA, f, ensure_ascii=False, separators=(',', ':'))
total_hex = sum(len(v) for v in HEX_DATA.values())
print(f'✓ hex.json: {total_hex}个海克斯')

# 3. 装备数据
with open(f'{OUT_DIR}/equipments.json', 'w', encoding='utf-8') as f:
    json.dump({
        'all': [list(eq) for eq in EQUIPMENT_LIST],
        'by_category': {k: [list(eq) for eq in v] for k, v in EQUIP_BY_CATEGORY.items()},
    }, f, ensure_ascii=False, separators=(',', ':'))
print(f'✓ equipments.json: {len(EQUIPMENT_LIST)}件装备')

print('\n所有数据已导出到 web/static/data/')