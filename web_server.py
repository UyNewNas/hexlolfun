'''
英雄联盟 海克斯大乱斗 5v5 文字版 — 网页后端
基于 lolhex_simulator.py 的逻辑，包装为 FastAPI JSON API
'''
import json
import os
import sys
import random
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 导入核心游戏逻辑
from lolhex_simulator import (
    Game, Champion, ALL_CHAMPIONS, HEX_DATA, EQUIPMENT_LIST,
    EQUIP_BY_CATEGORY, LANE_NAMES, HEX_LEVELS, BL_NEXUS, RD_NEXUS,
)

# ============================================================
# Data Dragon 版本（用于加载英雄头像/splash）
# ============================================================
DDRAGON_VERSION = "16.10.1"
DDRAGON_BASE = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img"

app = FastAPI(title="海克斯大乱斗 文字版")

# 静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 全局游戏实例（单局）
_game: Optional[Game] = None


# ============================================================
# Pydantic 模型
# ============================================================
class StartGameRequest(BaseModel):
    champion_id: str
    ally_diff: str = "medium"
    enemy_diff: str = "medium"


class ActionRequest(BaseModel):
    action: str


class BuyRequest(BaseModel):
    item_index: int


class HexSelectRequest(BaseModel):
    option_index: int


# ============================================================
# 序列化辅助
# ============================================================
def serialize_champion(c: Champion) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "title": c.title,
        "level": c.level,
        "exp": c.exp,
        "gold": c.gold,
        "kills": c.kills,
        "deaths": c.deaths,
        "assists": c.assists,
        "position": c.position,
        "position_name": LANE_NAMES[c.position],
        "team": c.team,
        "alive": c.alive,
        "respawn_timer": c.respawn_timer,
        "hp": c.hp,
        "max_hp": c.max_hp,
        "mana": getattr(c, 'mana', 0),
        "max_mana": getattr(c, 'max_mana', 0),
        "ad": round(c.ad, 1),
        "ap": round(c.ap, 1),
        "armor": round(c.armor, 1),
        "mr": round(c.mr, 1),
        "attack_speed": round(c.attack_speed, 2),
        "move_speed": c.move_speed,
        "crit": round(c.crit, 2),
        "items": c.items,
        "hex_augments": [h for h in c.hex_augments if h != '__pending__'],
        "can_shop": c.can_shop,
        # 客户端用
        "square_url": f"{DDRAGON_BASE}/champion/{c.id}.png",
        "splash_url": f"https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{c.id}_0.jpg",
    }


def serialize_game() -> dict:
    g = _game
    if g is None:
        return {}

    # 塔
    blue_towers = []
    red_towers = []
    for pos, t in g.blue_team.towers.items():
        blue_towers.append({
            "position": pos, "level": t.level, "alive": t.alive,
            "hp": t.hp, "max_hp": t.max_hp, "name": t.get_name(),
        })
    for pos, t in g.red_team.towers.items():
        red_towers.append({
            "position": pos, "level": t.level, "alive": t.alive,
            "hp": t.hp, "max_hp": t.max_hp, "name": t.get_name(),
        })

    # 水晶
    blue_inhib = g.blue_team.inhibitor
    red_inhib = g.red_team.inhibitor

    # 基地
    nexus_hp = getattr(g, '_nexus_hp', {BL_NEXUS: 5000, RD_NEXUS: 5000})

    # 小兵
    minions_data = []
    for m in g.minions:
        if m.alive:
            minions_data.append({
                "team": m.team, "position": m.position,
                "is_siege": m.is_siege,
            })

    # 海克斯选择待选
    pending_hex = getattr(g, '_pending_hex', None)

    return {
        "round": g.round_count,
        "game_time": g.game_time,
        "game_over": g.game_over,
        "winner": g.winner,
        "player_id": g.player.id,
        "champions": [serialize_champion(c) for c in g.get_all_champions()],
        "blue_towers": blue_towers,
        "red_towers": red_towers,
        "blue_inhib": {
            "alive": blue_inhib.alive, "hp": blue_inhib.hp, "max_hp": blue_inhib.max_hp
        } if blue_inhib else None,
        "red_inhib": {
            "alive": red_inhib.alive, "hp": red_inhib.hp, "max_hp": red_inhib.max_hp
        } if red_inhib else None,
        "blue_nexus": {"alive": g.blue_team.nexus_alive, "hp": nexus_hp.get(BL_NEXUS, 5000), "max_hp": 5000},
        "red_nexus": {"alive": g.red_team.nexus_alive, "hp": nexus_hp.get(RD_NEXUS, 5000), "max_hp": 5000},
        "minions": minions_data,
        "action_log": g.action_log,
        "pending_hex": pending_hex,
        "lane_names": LANE_NAMES,
    }


# ============================================================
# 路由 — 页面
# ============================================================
@app.get("/")
async def index():
    return FileResponse("web/static/index.html")


@app.get("/champselect")
async def champ_select():
    return FileResponse("web/static/champselect.html")


@app.get("/loading")
async def loading():
    return FileResponse("web/static/loading.html")


@app.get("/game")
async def game_page():
    return FileResponse("web/static/game.html")


# ============================================================
# 路由 — API
# ============================================================
@app.get("/api/champions")
async def list_champions():
    """返回所有可选英雄的精简列表（给选人页用）"""
    result = []
    for cid, c in ALL_CHAMPIONS.items():
        result.append({
            "id": cid,
            "name": c['name'],
            "title": c['title'],
            "tags": c['tags'],
            "square_url": f"{DDRAGON_BASE}/champion/{cid}.png",
            "splash_url": f"https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{cid}_0.jpg",
        })
    # 按名字排序
    result.sort(key=lambda x: x['name'])
    return result


@app.post("/api/game/start")
async def start_game(req: StartGameRequest):
    """开始新游戏"""
    global _game
    if req.champion_id not in ALL_CHAMPIONS:
        raise HTTPException(400, f"未知英雄: {req.champion_id}")
    _game = Game(req.champion_id, req.ally_diff, req.enemy_diff)
    return {"ok": True, "redirect": "/loading"}


@app.get("/api/game/state")
async def get_state():
    """获取完整游戏状态"""
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    return serialize_game()


@app.post("/api/game/action")
async def do_action(req: ActionRequest):
    """执行玩家指令"""
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    if _game.game_over:
        raise HTTPException(400, "游戏已结束")
    # 如果有海克斯待选，必须先选
    if hasattr(_game, '_pending_hex') and _game._pending_hex:
        raise HTTPException(400, "请先选择海克斯")
    _game.process_round(req.action)
    return {
        "state": serialize_game(),
        "action_log": _game.action_log,
    }


@app.get("/api/shop")
async def get_shop():
    """获取商店（死亡时可用）"""
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    return _game.show_shop()


@app.post("/api/shop/buy")
async def buy_item(req: BuyRequest):
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    result = _game.buy_item(req.item_index)
    return {"message": result, "state": serialize_game()}


@app.get("/api/hex")
async def get_hex():
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    return _game.show_hex_selection()


@app.post("/api/hex/select")
async def select_hex(req: HexSelectRequest):
    if _game is None:
        raise HTTPException(404, "游戏未开始")
    result = _game.select_hex(_game.player.id, req.option_index)
    return {"message": result, "state": serialize_game()}


@app.get("/api/hex/options")
async def get_hex_options():
    """给加载页用的海克斯预览"""
    return HEX_DATA


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)