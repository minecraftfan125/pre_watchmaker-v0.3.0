import os
from PyQt5.QtWidgets import (
    QWidget,
    QScrollArea,
    QSizePolicy,
    QPushButton,
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
    QSize,
)
from PyQt5.QtGui import (
    QPixmap,
    QIcon,
)
from common import FlowLayout
from edit_view.drag_effect import *


@Dragable("name")
class ComponentButton(QPushButton):
    """組件按鈕類，支持拖拽"""

    def __init__(self, image_path, tooltip_text, signal, parent=None, name=None):
        super().__init__(parent)
        self.setObjectName("componentButton")
        self.setFixedSize(60, 60)
        self.setToolTip(tooltip_text)
        self.image_path = image_path
        self.name = tooltip_text.replace(" ", "_") if name is None else name
        self.signal = signal

        # 載入圖片並設置為按鈕圖示
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 等比例縮放圖片以適應按鈕
            scaled_pixmap = pixmap.scaled(
                50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon = QIcon(scaled_pixmap)
            self.setIcon(icon)
            self.setIconSize(scaled_pixmap.size())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.signal.emit(self.name)


def _generate_tooltip(filename):
    """從文件名生成 tooltip 文字"""
    # 去除 btn_ 前綴和 .png 後綴
    name = filename.replace("btn_", "").replace(".png", "")
    # 將下劃線替換為空格
    name = name.replace("_", " ")
    # 首字母大寫
    return name


def _create_component_buttons(self, signal, data=[""]):
    """創建組件按鈕"""
    current_dir = os.path.dirname(__file__)
    # 2. 取得目前目錄的「父目錄」
    current_dir = os.path.dirname(current_dir)
    # 搜索所有 btn_ 開頭的圖片
    image_folders = ["img/edit"]
    button_data = []

    for folder in image_folders:
        folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.startswith("btn_") and filename.endswith(".png"):
                    image_path = os.path.join(folder_path, filename)
                    # 生成 tooltip 文字
                    tooltip = _generate_tooltip(filename)
                    button_data.append((image_path, tooltip))

    return [ComponentButton(data[0], data[1], signal, self) for data in button_data]

class ComponentPanel(QScrollArea):
    add_component = pyqtSignal(object, object)
    button_trigger = pyqtSignal(object)

    def __init__(self, data=None, signal=None, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWidgetResizable(True)
        self.setObjectName("componentsScroll")
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizePolicy(
            QSizePolicy.Preferred,  # width
            QSizePolicy.Preferred,  # height（非 Expanding）
        )
        self.setMaximumWidth(440)
        self.set_ui()

    def set_ui(self):
        # 創建內部容器 widget
        self.content_widget = QWidget()
        self.content_widget.setObjectName("componentsContent")
        self.buttons_layout = FlowLayout(self.content_widget)
        buttons = _create_component_buttons(self, self.button_trigger, self.data)
        for btn in buttons:
            self.buttons_layout.addWidget(btn)
        self.setWidget(self.content_widget)
        self.override = OverrideWidget(
            "drop here\nadd new item", "img/edit/com_drag.png", self
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.override.resize(self.size())

    def dragEnterEvent(self, event):
        """拖拽進入時接受事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.is_drag_over = True
            self.override.hide()

    def dragMoveEvent(self, event):
        """拖拽移動時更新"""
        super().dragMoveEvent(event)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """拖拽離開時重置"""
        self.is_drag_over = False
        self.override.show()

    def dropEvent(self, event):
        self.override.hide()

    def required_visual_effects(self, event):
        return event.pos(), QSize(60, 60)