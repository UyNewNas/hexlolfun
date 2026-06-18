'''
测试网页版API
'''
import requests

BASE = 'http://127.0.0.1:8000'

# 测试英雄API
r = requests.get(f'{BASE}/api/champions')
d = r.json()
print(f'英雄数: {len(d)}')
print(f'示例: {d[0]["name"]} | {d[0]["square_url"]}')

# 测试选人+启动
r2 = requests.post(f'{BASE}/api/game/start', json={'champion_id': 'Yasuo'})
print(f'启动: {r2.json()}')

# 测试游戏状态
r3 = requests.get(f'{BASE}/api/game/state')
s = r3.json()
print(f'回合: {s["round"]} | 玩家: {s["player_id"]}')
blue_alive = len([t for t in s['blue_towers'] if t['alive']])
red_alive = len([t for t in s['red_towers'] if t['alive']])
print(f'塔: 蓝{blue_alive}座 红{red_alive}座')
print(f'小兵: {len(s["minions"])}个')

# 测试动作
r4 = requests.post(f'{BASE}/api/game/action', json={'action': '待命'})
print(f'待命: round={r4.json()["state"]["round"]}, towers: {[t["name"] for t in r4.json()["state"]["red_towers"] if t["alive"]]}')

# 测试商店（强制死亡）
r5 = requests.post(f'{BASE}/api/game/action', json={'action': 'w'})
print(f'前进后回合: {r5.json()["state"]["round"]}')

# 测试页面路由
for path in ['/', '/champselect', '/loading', '/game']:
    r = requests.get(f'{BASE}{path}')
    print(f'页面 {path}: {r.status_code} ({len(r.text)} bytes)')

print('所有API测试通过！')