# -*- coding: utf-8 -*-
"""Windows 开机自启：写入当前用户注册表 Run 项。非 Windows 平台安全降级。"""
import sys
import os

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VoiceBroadcastReminder"


def _exe_path():
    """打包后取 exe 路径；源码运行时取 pythonw 解释器 + 主脚本。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return f'"{pyw}" "{main_py}"'


def is_enabled():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable():
    if sys.platform != "win32":
        return False, "仅支持 Windows 平台"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _exe_path())
        return True, "已开启开机自启"
    except Exception as e:
        return False, f"设置失败：{e}"


def disable():
    if sys.platform != "win32":
        return False, "仅支持 Windows 平台"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        return True, "已关闭开机自启"
    except Exception as e:
        return False, f"取消失败：{e}"
