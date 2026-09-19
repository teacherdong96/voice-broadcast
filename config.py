# -*- coding: utf-8 -*-
"""配置读写：任务列表与全局设置持久化到 config.json"""
import json
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULTS = {
    "auto_start": False,
    "volume": 1.0,        # 0.0 ~ 1.0
    "rate": 180,          # 语速，字/分钟
    "banner_duration": 0, # 横幅停留秒数，0=不自动关闭
    "tasks": []           # 每项: {id, content, time, weekdays:[1..7], enabled}
}


def load():
    data = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                data.update(saved)
        except Exception:
            pass
    if not isinstance(data.get("tasks"), list):
        data["tasks"] = []
    return data


def save(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save config failed:", e)
