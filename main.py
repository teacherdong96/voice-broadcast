# -*- coding: utf-8 -*-
"""定时语音播报主程序：主界面 + 系统托盘 + 定时调度 + 横幅 + TTS。"""
import sys
import datetime
import uuid

from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTimeEdit, QCheckBox, QListWidget,
    QListWidgetItem, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QGroupBox, QSpinBox, QDoubleSpinBox,
)

import config
import autostart
from speech import Speaker
from banner import Banner

WEEK_LABELS = ["一", "二", "三", "四", "五", "六", "日"]  # index 0..6 对应周一..周日


def weekday_today():
    """返回今天是周几：周一=1 ... 周日=7"""
    return datetime.datetime.now().isoweekday()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.speaker = Speaker(rate=self.cfg.get("rate", 180),
                               volume=self.cfg.get("volume", 1.0))
        self.banner = None
        self.last_fired = set()  # 避免同一分钟重复触发 (task_id, YYYYMMDDHHMM)

        self.setWindowTitle("定时语音播报")
        self.resize(760, 620)

        self._build_ui()
        self._build_tray()
        self._refresh_task_list()
        self._refresh_autostart_state()

        # 每秒检查一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # 顶部：全局设置
        top_box = QGroupBox("全局设置")
        top_layout = QHBoxLayout(top_box)

        self.chk_autostart = QCheckBox("开机自启")
        self.chk_autostart.stateChanged.connect(self._toggle_autostart)
        top_layout.addWidget(self.chk_autostart)

        top_layout.addWidget(QLabel("音量"))
        self.spin_vol = QDoubleSpinBox()
        self.spin_vol.setRange(0.0, 1.0)
        self.spin_vol.setSingleStep(0.1)
        self.spin_vol.setValue(float(self.cfg.get("volume", 1.0)))
        self.spin_vol.valueChanged.connect(self._apply_speech_params)
        top_layout.addWidget(self.spin_vol)

        top_layout.addWidget(QLabel("语速"))
        self.spin_rate = QSpinBox()
        self.spin_rate.setRange(80, 400)
        self.spin_rate.setValue(int(self.cfg.get("rate", 180)))
        self.spin_rate.valueChanged.connect(self._apply_speech_params)
        top_layout.addWidget(self.spin_rate)

        top_layout.addWidget(QLabel("横幅停留(秒,0=不自动关)"))
        self.spin_banner = QSpinBox()
        self.spin_banner.setRange(0, 3600)
        self.spin_banner.setValue(int(self.cfg.get("banner_duration", 0)))
        self.spin_banner.valueChanged.connect(self._apply_banner_duration)
        top_layout.addWidget(self.spin_banner)

        top_layout.addStretch()

        self.btn_hide = QPushButton("最小化到托盘")
        self.btn_hide.clicked.connect(self.hide_to_tray)
        top_layout.addWidget(self.btn_hide)

        root.addWidget(top_box)

        # 任务设置区
        edit_box = QGroupBox("新建 / 编辑播报任务")
        edit_layout = QVBoxLayout(edit_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("播报内容："))
        self.edit_content = QLineEdit()
        self.edit_content.setPlaceholderText("例如：下午三点了，记得喝水休息一下")
        row1.addWidget(self.edit_content, 1)
        edit_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("执行时间："))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime().addSecs(60))
        row2.addWidget(self.time_edit)

        row2.addSpacing(20)
        row2.addWidget(QLabel("重复星期："))
        self.week_checks = []
        for i, label in enumerate(WEEK_LABELS):
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.week_checks.append(cb)
            row2.addWidget(cb)
        row2.addStretch()

        self.btn_save = QPushButton("添加任务")
        self.btn_save.clicked.connect(self._add_task)
        row2.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("取消编辑")
        self.btn_cancel.clicked.connect(self._reset_editor)
        self.btn_cancel.hide()
        row2.addWidget(self.btn_cancel)

        edit_layout.addLayout(row2)
        root.addWidget(edit_box)

        # 已有任务区
        list_box = QGroupBox("已有任务（勾选 = 启用；单击内容 = 编辑；右键 = 删除）")
        list_layout = QVBoxLayout(list_box)
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self._on_item_clicked)
        self.task_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self._show_task_menu)
        list_layout.addWidget(self.task_list)
        root.addWidget(list_box, 1)

        self._editing_id = None
        self._loading_list = False  # 防止刷新时触发 itemChanged

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        # 用系统标准图标，避免依赖外部图标文件
        self.tray.setIcon(self.style().standardIcon(self.style().SP_MediaVolume))
        self.tray.setToolTip("定时语音播报")

        menu = QMenu()
        act_show = QAction("显示主界面", self)
        act_show.triggered.connect(self.showNormal)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    # ---------- 托盘 / 关闭 ----------
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def hide_to_tray(self):
        self.hide()
        self.tray.showMessage("定时语音播报", "已最小化到托盘后台运行，双击图标打开主界面。",
                             QSystemTrayIcon.Information, 2000)

    def closeEvent(self, event):
        # 点 X 最小化到托盘而不是退出
        event.ignore()
        self.hide_to_tray()

    def _quit_app(self):
        self.speaker.stop()
        self.tray.hide()
        QApplication.instance().quit()

    # ---------- 开机自启 ----------
    def _refresh_autostart_state(self):
        self.chk_autostart.blockSignals(True)
        self.chk_autostart.setChecked(autostart.is_enabled())
        self.chk_autostart.blockSignals(False)

    def _toggle_autostart(self, state):
        if state == Qt.Checked:
            ok, msg = autostart.enable()
        else:
            ok, msg = autostart.disable()
        self.cfg["auto_start"] = bool(state == Qt.Checked)
        config.save(self.cfg)
        if not ok:
            QMessageBox.warning(self, "提示", msg)

    # ---------- 语音参数 ----------
    def _apply_speech_params(self):
        r = int(self.spin_rate.value())
        v = float(self.spin_vol.value())
        self.speaker.set_params(rate=r, volume=v)
        self.cfg["rate"] = r
        self.cfg["volume"] = v
        config.save(self.cfg)

    def _apply_banner_duration(self):
        self.cfg["banner_duration"] = int(self.spin_banner.value())
        config.save(self.cfg)

    # ---------- 任务 CRUD ----------
    def _selected_weekdays(self):
        return [i + 1 for i, cb in enumerate(self.week_checks) if cb.isChecked()]

    def _set_weekdays(self, days):
        for i, cb in enumerate(self.week_checks):
            cb.setChecked((i + 1) in days)

    def _add_task(self):
        content = self.edit_content.text().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请填写播报内容")
            return
        days = self._selected_weekdays()
        if not days:
            QMessageBox.warning(self, "提示", "请至少选择一个星期")
        hhmm = self.time_edit.time().toString("HH:mm")

        if self._editing_id:
            for t in self.cfg["tasks"]:
                if t["id"] == self._editing_id:
                    t["content"] = content
                    t["time"] = hhmm
                    t["weekdays"] = days
                    break
            self._editing_id = None
            self.btn_save.setText("添加任务")
            self.btn_cancel.hide()
        else:
            self.cfg["tasks"].append({
                "id": uuid.uuid4().hex,
                "content": content,
                "time": hhmm,
                "weekdays": days,
                "enabled": True,
            })
        config.save(self.cfg)
        self._reset_editor()
        self._refresh_task_list()

    def _reset_editor(self):
        self.edit_content.clear()
        self._editing_id = None
        self.btn_save.setText("添加任务")
        self.btn_cancel.hide()

    def _refresh_task_list(self):
        self._loading_list = True
        self.task_list.clear()
        for t in self.cfg["tasks"]:
            days_str = "、".join(WEEK_LABELS[d - 1] for d in sorted(t["weekdays"]))
            text = f"{t['time']}  周{days_str}   {t['content']}"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if t.get("enabled", True) else Qt.Unchecked)
            item.setData(Qt.UserRole, t["id"])
            self.task_list.addItem(item)
        self._loading_list = False

    def _on_item_clicked(self, item):
        # 复选框状态变化 → 更新 enabled
        tid = item.data(Qt.UserRole)
        enabled = item.checkState() == Qt.Checked
        for t in self.cfg["tasks"]:
            if t["id"] == tid:
                if t.get("enabled", True) != enabled:
                    t["enabled"] = enabled
                    config.save(self.cfg)
                break
        # 如果点的不是复选框区域，则把任务加载到编辑区
        # 通过判断鼠标位置是否在 checkbox 列来区分：简单起见，只要复选框被点击就不进编辑
        # 这里采用：单击复选框切换开关，单击文字部分进入编辑。
        # 由于 QListWidget 复选框占左侧固定宽度，用 view 上的 x 坐标判断
        pos = self.task_list.viewport().mapFromGlobal(self.cursor().pos())
        rect = self.task_list.visualItemRect(item)
        # 复选框宽度约 20~24px
        if pos.x() > rect.left() + 28:
            self._load_into_editor(tid)

    def _load_into_editor(self, tid):
        for t in self.cfg["tasks"]:
            if t["id"] == tid:
                self._editing_id = tid
                self.edit_content.setText(t["content"])
                hh, mm = map(int, t["time"].split(":"))
                self.time_edit.setTime(QTime(hh, mm))
                self._set_weekdays(t["weekdays"])
                self.btn_save.setText("保存修改")
                self.btn_cancel.show()
                break

    def _show_task_menu(self, pos):
        item = self.task_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("编辑")
        act_del = menu.addAction("删除")
        chosen = menu.exec_(self.task_list.viewport().mapToGlobal(pos))
        tid = item.data(Qt.UserRole)
        if chosen == act_edit:
            self._load_into_editor(tid)
        elif chosen == act_del:
            ret = QMessageBox.question(self, "删除任务", "确认删除该任务？")
            if ret == QMessageBox.Yes:
                self.cfg["tasks"] = [t for t in self.cfg["tasks"] if t["id"] != tid]
                config.save(self.cfg)
                self._refresh_task_list()

    # ---------- 调度 ----------
    def _tick(self):
        now = datetime.datetime.now()
        hhmm = now.strftime("%H:%M")
        wd = now.isoweekday()
        minute_key = now.strftime("%Y%m%d%H%M")

        for t in self.cfg["tasks"]:
            if not t.get("enabled", True):
                continue
            if t["time"] != hhmm:
                continue
            if wd not in t["weekdays"]:
                continue
            key = (t["id"], minute_key)
            if key in self.last_fired:
                continue
            self.last_fired.add(key)
            self._fire(t)

        # 清理过旧的 key，避免内存膨胀
        if len(self.last_fired) > 500:
            self.last_fired = {k for k in self.last_fired if k[1] >= minute_key}

    def _fire(self, task):
        # 语音播报
        self.speaker.speak(task["content"])
        # 横幅
        if self.banner is not None:
            try:
                self.banner.close()
            except Exception:
                pass
        self.banner = Banner(task["content"],
                             duration=int(self.cfg.get("banner_duration", 0)),
                             on_close=lambda: setattr(self, "banner", None))
        self.banner.show()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，走托盘

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
