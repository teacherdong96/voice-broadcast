# -*- coding: utf-8 -*-
"""播报横幅：针对教室希沃触控大屏优化——
- 占据屏幕一半（宽=屏宽50%，高=屏高50%），屏幕居中
- 大字体、大关闭按钮，方便触控
- 点击横幅任意处或右上角大按钮关闭
"""
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtGui import QColor


class Banner(QWidget):
    def __init__(self, content, duration=0, on_close=None, parent=None):
        super().__init__(parent)
        self.on_close_cb = on_close
        self.duration = duration

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        # 半屏：宽=屏宽一半，高=屏高一半，居中
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        width = int(geo.width() * 0.5)
        height = int(geo.height() * 0.5)
        x = geo.left() + (geo.width() - width) // 2
        y = geo.top() + (geo.height() - height) // 2
        self.setGeometry(QRect(x, y, width, height))

        # 容器（白底圆角 + 阴影，教室大屏上要够醒目）
        self.container = QWidget(self)
        self.container.setObjectName("bannerContainer")
        self.container.setStyleSheet("""
            #bannerContainer {
                background-color: #ffffff;
                border: 6px solid #2b6cb0;
                border-radius: 24px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(60)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(30)

        # 顶部：标题 + 大关闭按钮
        top = QHBoxLayout()
        title = QLabel("🔊 定时播报提醒")
        title.setStyleSheet("color:#2b6cb0; font-weight:bold;")
        title_font = QFont()
        title_font.setPointSize(24)
        title.setFont(title_font)

        close_btn = QPushButton("× 关闭")
        close_btn.setFixedSize(160, 80)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                color:#ffffff; background-color:#e53e3e;
                border:none; border-radius:16px;
                font-size:26px; font-weight:bold;
            }
            QPushButton:hover { background-color:#c53030; }
            QPushButton:pressed { background-color:#9b2c2c; }
        """)
        close_btn.clicked.connect(self.close_banner)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(close_btn)

        # 正文：教室后排也要看清
        body = QLabel(content)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        body.setStyleSheet("color:#1a202c;")
        body_font = QFont()
        body_font.setPointSize(48)
        body_font.setBold(True)
        body.setFont(body_font)

        # 底部提示
        tip = QLabel("（点击横幅任意处即可关闭）")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color:#a0aec0;")
        tip_font = QFont()
        tip_font.setPointSize(14)
        tip.setFont(tip_font)

        layout.addLayout(top)
        layout.addWidget(body, 1)
        layout.addWidget(tip)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.container)

        # 自动关闭
        if self.duration and self.duration > 0:
            QTimer.singleShot(self.duration * 1000, self.close_banner)

    def mousePressEvent(self, event):
        # 点击横幅任意处关闭
        if event.button() == Qt.LeftButton:
            self.close_banner()
        super().mousePressEvent(event)

    def close_banner(self):
        try:
            if callable(self.on_close_cb):
                self.on_close_cb()
        except Exception:
            pass
        self.close()
