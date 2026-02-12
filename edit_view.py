import os
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QScrollArea,
    QSizePolicy,
    QPushButton,
    QGridLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QGraphicsScene,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QGraphicsView,
    QRadioButton,
    QLineEdit,
    QComboBox,
    QColorDialog,
    QFileDialog,
    QGraphicsItem,
    QGraphicsEllipseItem,
)
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QMimeData,
    pyqtSignal,
    QSize,
    QThread,
    QTimer,
    QEvent,
    QRect,
    QPropertyAnimation,
    QEasingCurve,
    QObject,
)
from PyQt5.QtGui import QPixmap, QIcon, QDrag, QCursor, QColor,QPainter,QPen,QBrush
from script_view import ScriptView
from common import FlowLayout, StackWidget, FontManager
import components
import summon_obj


def load_style():
    """載入編輯視圖樣式"""
    style_path = os.path.join(os.path.dirname(__file__), "style", "edit_view.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Style file not found: {style_path}")
        return ""


def Dragable(cls):
    original_mousePress = cls.mousePressEvent
    original_mouseMove = cls.mouseMoveEvent
    original_mouseRelease = cls.mouseReleaseEvent

    cls.drag_start_position = None
    cls.draged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        original_mouseMove(self, event)
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        # 检查移动距离是否超过启动拖拽的阈值
        if (event.pos() - self.drag_start_position).manhattanLength() < 5:
            return
        # 创建拖拽对象
        self.come_from = True
        drag = QDrag(self)
        mime_data = QMimeData()
        # 存储组件信息（tooltip）
        mime_data.setText(self.name)
        drag.setMimeData(mime_data)
        self.signal.emit(self.name, self.attributes)
        # 执行拖拽
        result = drag.exec_(Qt.CopyAction)
        if result is result:
            self.signal.emit(self.name, "drop")
        # 重置拖拽起始位置
        self.drag_start_position = None
        self.draged = True

    def mouseReleaseEvent(self, event):
        if self.draged is False:
            original_mousePress(self, event)
            self.draged = False
        original_mouseRelease(self, event)

    cls.mousePressEvent = mousePressEvent
    cls.mouseMoveEvent = mouseMoveEvent
    cls.mouseReleaseEvent = mouseReleaseEvent
    return cls


@Dragable
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

    def get_attribute(self):
        return self.attributes

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if not hasattr(self, "attributes"):
            self.attributes = getattr(components, self.name)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not hasattr(self, "attributes"):
            self.attributes = getattr(components, self.name)
        self.signal.emit(self.name, self.attributes)


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
    # 搜索所有 btn_ 開頭的圖片
    image_folders = ["img/edit"]
    button_data = []

    for folder in image_folders:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.startswith("btn_") and filename.endswith(".png"):
                    image_path = os.path.join(folder_path, filename)
                    # 生成 tooltip 文字
                    tooltip = _generate_tooltip(filename)
                    button_data.append((image_path, tooltip))

    return [ComponentButton(data[0], data[1], signal, self) for data in button_data]


class OverrideWidget(QWidget):
    def __init__(self, text, img_path, parent=None):
        super().__init__(parent)
        # self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        # 設定半透明背景
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            background-color: rgba(255, 255, 255, 80);
            border: 3px solid #3d3d3d;
        """)
        information_layout = QVBoxLayout(self)
        information_layout.setAlignment(Qt.AlignCenter)

        Indication = QPixmap(img_path)
        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        # img.setMaximumSize(100,100)
        img.setPixmap(Indication)
        img.setStyleSheet("""
            background-color: transparent;
            border: None;
        """)
        information_layout.addWidget(img)

        self.information = QLabel()
        self.information.setAlignment(Qt.AlignCenter)
        self.information.setMaximumSize(200, 50)
        self.information.setText(text)
        self.information.setStyleSheet("""
            background-color: transparent; color: #3d3d3d;
            font-weight:bold;
            border: None;
        """)
        information_layout.addWidget(self.information)
        self.hide()

    def change_text(self, text):
        self.information.setText(text)

    def show(self):
        self.raise_()
        super().show()


class DragVisual(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("border: 3px solid #0078D4;")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

        # 用 QPropertyAnimation 控制外框幾何
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(200)  # 動畫時間
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.animation = False

        self.last_time = None

    def change(self, pos, size):
        # 設定目標 geometry
        pos = QPoint(pos.x() - size.width() // 2, pos.y() - size.height() // 2)
        target = QRect(pos, size)

        # 如果第一次，就直接設置
        if not self.isVisible():
            self.setGeometry(target)
            self.raise_()
            self.show()
            return

        if target == self.last_time:
            return
        self.last_time = target

        # 若動畫正在跑，要先停止
        if self.anim.state() == QPropertyAnimation.Running:
            self.anim.stop()

        length = pos - self.pos()
        if length.manhattanLength() >= 20:
            self.animation = True
        if size != self.size():
            self.animation = True

        if self.animation == True:
            # 重新播放動畫
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target)
            self.anim.start()
            self.animation = False
        else:
            self.setGeometry(target)


class Exploror(QTreeWidget):
    def __init__(self, data=None, signal=None, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(200)
        self.override = OverrideWidget(
            "drop here\nadd new item", "img/edit/exp_drag.png", self
        )
        self.setAcceptDrops(True)
        self.send_all = signal

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

    def dragLeaveEvent(self, event):
        """拖拽離開時重置"""
        self.is_drag_over = False
        self.override.show()

    def dropEvent(self, event):
        self.override.hide()

    def required_visual_effects(self, event):
        return event.pos(), QSize(60, 60)


class WatchPreview(QGraphicsView):
    select = pyqtSignal(object)
    summon = pyqtSignal(object, object, object)
    receive = pyqtSignal(object, object, object)

    # 場景固定大小 (錶面尺寸)
    SCENE_SIZE = 454

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.scale = []
        self.hash_table = {}
        self.sence = QGraphicsScene()
        # 設定固定的場景範圍
        self.sence.setSceneRect(0, 0, self.SCENE_SIZE, self.SCENE_SIZE)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAcceptDrops(True)
        # 確保 viewport 也接受拖放
        self.viewport().setAcceptDrops(True)
        self.receive.connect(self.summon_component)
        self.setScene(self.sence)
        # 禁用滾動條
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 設置拖放模式
        self.setDragMode(QGraphicsView.NoDrag)
        self._background_circle = None
        self.set_ui()

    def set_ui(self):
        self.override = OverrideWidget(
            "drop here\nadd new item", "img/edit/view_drag.png", self
        )
        self._create_background_circle()

    def _create_background_circle(self):
        """創建背景圓形"""
        self._background_circle = QGraphicsEllipseItem()
        self._background_circle.setBrush(QBrush(QColor("#0e0e0e")))
        self._background_circle.setPen(QPen(Qt.NoPen))
        self._background_circle.setZValue(-1000)  # 確保在最底層
        self._background_circle.setAcceptDrops(False)  # 不接受拖放事件
        self._background_circle.setAcceptedMouseButtons(Qt.NoButton)  # 不接受滑鼠事件
        self.sence.addItem(self._background_circle)
        self._update_background_circle()

    def _update_background_circle(self):
        """更新背景圓形的大小和位置（使用場景座標）"""
        if self._background_circle is None:
            return

        margin = 50
        # 使用場景尺寸計算
        diameter = self.SCENE_SIZE - margin * 2

        # 圓心位於場景中心
        center = self.SCENE_SIZE / 2

        # 設置圓形的位置和大小
        self._background_circle.setRect(
            center - diameter / 2,
            center - diameter / 2,
            diameter,
            diameter
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.override.resize(self.size())
        # 強制縮放內容以符合視窗大小，保持長寬比
        self.fitInView(self.sence.sceneRect(), Qt.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        # 首次顯示時也要調整縮放
        self.fitInView(self.sence.sceneRect(), Qt.KeepAspectRatio)

    def paintEvent(self, a0):
        super().paintEvent(a0)

    def summon_component(self, hash_id, attribute, layer_type):
        print("y")
        """根據屬性和圖層類型創建元件並顯示在預覽區"""
        # 使用 summon_obj 的 create_layer 函數創建對應的圖層
        print(attribute)
        layer = summon_obj.create_layer(layer_type, attribute)

        # 設置初始位置 (從屬性中取得 X, Y)
        x = attribute.get("X", 0)
        y = attribute.get("Y", 0)

        # 將座標轉換為場景中心點位置
        center = self.SCENE_SIZE / 2
        layer.setPos(center + x, center + y)

        # 將元件添加到場景
        self.sence.addItem(layer)

        # 儲存到 hash_table
        self.hash_table[hash_id] = layer

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            self.select.emit(self.hash_table[watched])
        return False

    def dragEnterEvent(self, event):
        print("y")
        """拖拽進入時接受事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.is_drag_over = True
            self.override.hide()

    def dragLeaveEvent(self, event):
        """拖拽離開時重置"""
        self.is_drag_over = False
        self.override.show()

    def dragMoveEvent(self, event):
        """必須顯式接受移動事件，否則 dropEvent 不會觸發"""
        if event.mimeData().hasText():
            event.acceptProposedAction()  # 關鍵：直接告訴 Qt 這裡可以放
        else:
            event.ignore()

    def dropEvent(self, event):
        print("y")
        if event.mimeData().hasText():
            # 將視窗座標轉換為場景座標，並計算相對於中心的位置
            scene_pos = self.mapToScene(event.pos())
            center = self.SCENE_SIZE / 2
            x = int(scene_pos.x() - center)
            y = int(scene_pos.y() - center)
            self.summon.emit(event.mimeData().text(), (x, y), 0)
            event.acceptProposedAction()
        self.override.hide()

    def required_visual_effects(self, event):
        return event.pos(), QSize(60, 60)


class ComponentPanel(QScrollArea):
    add_component = pyqtSignal(object, object)
    button_trigger = pyqtSignal(object, object)

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

class AttributeForm(QScrollArea):
    """Scrollable form containing multiple attribute containers"""

    class AttributeContainer(QWidget):
        """單個屬性容器 - 儲存並顯示一個 attribute 值"""

        tip_signal = pyqtSignal(str)
        value_changed = pyqtSignal(object)
        open_script_editor = pyqtSignal(object)
        open_widget_editor = pyqtSignal(object, object)

        def __init__(self, attr_config, signal, parent=None):
            super().__init__(parent)
            self.attr_config = attr_config
            self.name = attr_config.get("name", "")
            self.attr_type = attr_config.get("type", "str")
            self.default = attr_config.get("default", "")
            self.description = attr_config.get("description", "")
            self.options = attr_config.get("options", [])
            self.signal = signal
            self._value = self.default
            self.signal.connect(self.set_value)
            self._create_ui()

        def _create_ui(self):
            self.left = QLabel(self.name)
            self.left.setObjectName("attrLabel")

            if self.attr_type == "str":
                self._create_str_ui()
            elif self.attr_type == "text":
                self._create_str_ui()
            elif self.attr_type == "int":
                self._create_int_ui()
            elif self.attr_type == "num":
                self._create_num_ui()
            elif self.attr_type == "number":
                self._create_num_ui()
            elif self.attr_type == "option":
                self._create_option_ui()
            elif self.attr_type == "color":
                self._create_color_ui()
            elif self.attr_type == "widget":
                self._create_widget_ui()
            elif self.attr_type == "bool":
                self._create_bool_ui()
            elif self.attr_type == "file":
                self._create_file_ui()
            else:
                self._create_str_ui()

            self.right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if len(self.name) <= 8:
                self.left.setFixedWidth(80)
                self.row_layout = QHBoxLayout(self)
                self.row_layout.setContentsMargins(0, 2, 0, 2)
                self.row_layout.setSpacing(8)
                self.row_layout.addWidget(self.left)
                self.row_layout.addWidget(self.right, 1)
                return
            self.row_layout = QVBoxLayout(self)
            self.row_layout.setContentsMargins(0, 2, 0, 2)
            self.row_layout.setSpacing(8)
            self.row_layout.addWidget(self.left)
            self.row_layout.addWidget(self.right, 1)

        def _create_str_ui(self):
            if self.attr_config["name"] == "Text":
                self.right = QWidget()
                right_layout = QHBoxLayout(self.right)
                right_layout.setContentsMargins(0, 0, 0, 0)
                right_layout.setSpacing(4)

                self.input = QLineEdit()
                self.input.setObjectName("attrInput")
                self.input.setText(str(self.default))
                self.input.textChanged.connect(self._on_text_changed)
                self.input.textChanged.connect(self.signal.emit)
                self.input.setAcceptDrops(False)
                right_layout.addWidget(self.input, 1)

                self.script_btn = QPushButton("_<")
                self.script_btn.setObjectName("scriptButton")
                self.script_btn.setFixedSize(30, 25)
                self.script_btn.clicked.connect(
                    lambda: self.open_script_editor.emit(self)
                )
                right_layout.addWidget(self.script_btn)
                return
            self.right = QLineEdit()
            self.right.setObjectName("attrInput")
            self.right.setText(str(self.default))
            self.right.textChanged.connect(self._on_text_changed)
            self.right.textChanged.connect(self.signal.emit)
            self.right.setAcceptDrops(False)

        def _create_int_ui(self):
            self.right = QLineEdit()
            self.right.setObjectName("attrInput")
            self.right.setText(str(self.default))
            self.right.textChanged.connect(self._on_text_changed)
            self.right.textChanged.connect(self.signal.emit)
            self.right.setAcceptDrops(False)

        def _create_num_ui(self):
            self.right = QWidget()
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            self.input.setText(str(self.default))
            self.input.textChanged.connect(self._on_text_changed)
            self.input.textChanged.connect(self.signal.emit)
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

            self.script_btn = QPushButton("_<")
            self.script_btn.setObjectName("scriptButton")
            self.script_btn.setFixedSize(30, 25)
            self.script_btn.clicked.connect(lambda: self.open_script_editor.emit(self))
            right_layout.addWidget(self.script_btn)

        def _create_option_ui(self):
            self.right = QComboBox()
            self.right.setObjectName("attrCombo")
            self.right.addItems([str(opt) for opt in self.options])
            index = self.right.findText(str(self.default))
            if index >= 0:
                self.right.setCurrentIndex(index)
            self.right.currentTextChanged.connect(self._on_combo_changed)
            self.right.currentTextChanged.connect(self.signal.emit)
            self.right.wheelEvent = lambda e: e.ignore()

        def _create_color_ui(self):
            self.right = QWidget()
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.color_btn = QPushButton()
            self.color_btn.setObjectName("colorButton")
            self.color_btn.setFixedSize(50, 25)
            self._current_color = (
                QColor(f"#{self.default}") if self.default else QColor("#ffffff")
            )
            self._update_color_button()
            self.color_btn.clicked.connect(self._on_color_clicked)
            right_layout.addWidget(self.color_btn)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            self.input.setText(str(self.default))
            self.input.textChanged.connect(self._on_color_text_changed)
            self.input.textChanged.connect(self.signal.emit)
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

        def _create_widget_ui(self):
            self.right = QPushButton()
            self.right.setObjectName("expandButton")
            self.right.setText(self.default.get("Display", "")) if isinstance(
                self.default, dict
            ) else str(self.default)
            self.right.clicked.connect(self._on_widget_clicked)

        def _on_widget_clicked(self):
            self.open_widget_editor.emit(self, self.default)

        def _create_bool_ui(self):
            self.right = QRadioButton()
            self.right.setObjectName("attrCombo")
            self.right.setChecked(self.default)
            self.right.clicked.connect(self._on_bool_changed)
            self.right.clicked.connect(self.signal.emit)

        def _on_bool_changed(self, text):
            self._value = text == "True"
            self.attr_config["default"] = self._value
            self.value_changed.emit(self._value)

        def _create_file_ui(self):
            self.right = QPushButton()
            self.right.setObjectName("fileButton")
            self._update_file_button_text()
            self.right.clicked.connect(self._on_file_clicked)

        def _update_file_button_text(self):
            """更新檔案按鈕的顯示文字"""
            if self._value and self._value != "":
                # 顯示檔案名稱（不含路徑）
                filename = os.path.basename(str(self._value))
                self.right.setText(filename)
            else:
                self.right.setText("None")

        def _on_file_clicked(self):
            """開啟檔案選擇對話框"""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "選擇檔案",
                "",
                "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.bmp);;3D Models (*.obj *.gltf *.glb)"
            )
            if file_path:
                self._value = file_path
                self.attr_config["default"] = file_path
                self._update_file_button_text()
                self.value_changed.emit(file_path)
                self.signal.emit(file_path)

        def _update_color_button(self):
            self.color_btn.setStyleSheet(
                f"background-color: {self._current_color.name()}; border: 1px solid #4d4d4d;"
            )

        def _on_text_changed(self, text):
            self._value = text
            self.attr_config["default"] = text
            self.value_changed.emit(text)

        def _on_combo_changed(self, text):
            self._value = text
            self.attr_config["default"] = text
            self.value_changed.emit(text)

        def _on_color_clicked(self):
            color = QColorDialog.getColor(self._current_color, self, "選擇顏色")
            if color.isValid():
                self._current_color = color
                self._update_color_button()
                hex_color = color.name()[1:]
                self.input.setText(hex_color)
                self._value = hex_color
                self.value_changed.emit(hex_color)

        def _on_color_text_changed(self, text):
            self._value = text
            self.attr_config["default"] = text
            try:
                color = QColor(f"#{text}" if not text.startswith("#") else text)
                if color.isValid():
                    self._current_color = color
                    self._update_color_button()
            except:
                pass
            self.value_changed.emit(text)

        def get_value(self):
            return self._value

        def valid(self, text):
            try:
                text = str(text)
            except:
                return self._value
            if text == self._value:
                return self._value
            return text

        def set_value(self, value):
            if self._value == self.valid(value):
                return
            self._value = value
            if self.attr_type == "option":
                index = self.right.findText(str(value))
                if index >= 0:
                    self.right.setCurrentIndex(index)
            elif self.attr_type == "color":
                self.input.setText(str(value))
                try:
                    self._current_color = QColor(f"#{value}")
                    self._update_color_button()
                except:
                    pass
            elif self.attr_type in ("num", "number"):
                self.input.setText(str(value))
            elif self.attr_type == "bool":
                index = 0 if value else 1
                self.right.setCurrentIndex(index)
            elif self.attr_type == "widget":
                display_text = (
                    value.get("Display", "") if isinstance(value, dict) else str(value)
                )
                self.display_field.setText(display_text)
            elif self.attr_type == "file":
                self._update_file_button_text()
            else:
                self.right.setText(str(value))

        def enterEvent(self, event):
            super().enterEvent(event)
            self.tip_signal.emit(self.description)

        def leaveEvent(self, event):
            super().leaveEvent(event)
            self.tip_signal.emit("")

    # AttributeForm 類別信號
    request_script_editor = pyqtSignal(object)
    open_widget_editor = pyqtSignal(object, object)
    value_changed = pyqtSignal(str, object)
    go_back=pyqtSignal()
    go_home=pyqtSignal()

    def __init__(self, attribute_list, parent=None):
        super().__init__(parent)
        self._setup_scroll_area()
        self._containers = {}
        self._layer_type = None
        if attribute_list[0]["TYPE"]!="baseLayer":
            self.back_container()
        self._parse_and_build(attribute_list)

    def _setup_scroll_area(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        self._main_widget = QWidget()
        self.setWidget(self._main_widget)
        self._vlayout = QVBoxLayout(self._main_widget)
        self._vlayout.setAlignment(Qt.AlignTop)
        self._vlayout.setContentsMargins(10, 20, 10, 20)
        self._vlayout.setSpacing(4)

    def back_container(self):
        hlayout=QHBoxLayout()
        back=QPushButton("< Back")
        home=QPushButton("Home")
        hlayout.addWidget(back)
        hlayout.addStretch()
        hlayout.addWidget(home)
        back.clicked.connect(self.go_back.emit)
        home.clicked.connect(self.go_home.emit)
        self._vlayout.addLayout(hlayout)

    def _parse_and_build(self, attribute_list):
        import copy
        import components.common as common_defs

        attr_list = copy.deepcopy(attribute_list)

        # 取得 layer type
        for item in attr_list:
            if "TYPE" in item:
                self._layer_type = item["TYPE"]
                break

        layer_def = (
            getattr(common_defs, self._layer_type, {}) if self._layer_type else {}
        )

        # 建立包含所有 attribute 的字典（合併 layer_def 和 attr_list 的 key）
        all_attrs = dict(layer_def)
        for item in attr_list:
            for key, val in item.items():
                if key not in ("TYPE", "description") and key not in all_attrs:
                    all_attrs[key] = val

        self.attribute = summon_obj.Attribute(all_attrs)
        self.attribute.set_default(dict([list(att.items())[0] for att in attr_list]))

        for item in attr_list:
            if "TYPE" in item:
                continue

            attr_name = None
            attr_value = None
            description = item.get("description", "")

            for key, val in item.items():
                if key != "description":
                    attr_name = key
                    attr_value = val
                    break

            if attr_name is None:
                continue

            type_info = self._get_type_info(layer_def, attr_name)
            config = {
                "name": attr_name,
                "type": type_info["type"],
                "default": attr_value,
                "description": description,
                "options": type_info.get("options", []),
            }
            self._add_container(config)

        self._vlayout.addStretch()

    def get_attribute(self):
        return self.attribute

    def _get_type_info(self, layer_def, attr_name):
        if attr_name not in layer_def:
            return {"type": "str", "options": []}

        type_spec = layer_def[attr_name]

        if type_spec == "str":
            return {"type": "str"}
        elif type_spec == "text":
            return {"type": "text"}
        elif type_spec == "color":
            return {"type": "color"}
        elif type_spec == "bool":
            return {"type": "bool"}
        elif type_spec == "file":
            return {"type": "file"}
        elif type_spec == "widget":
            return {"type": "widget"}
        elif type_spec == "font":
            # 從 FontManager 獲取可用字型列表
            font_manager = FontManager()
            fonts = font_manager.get_available_fonts()
            if not fonts:
                fonts = ["Arial"]  # 預設字型
            return {"type": "option", "options": fonts}
        elif isinstance(type_spec, tuple) and len(type_spec) == 3:
            if type_spec[2] == 1:
                return {"type": "int"}
            else:
                return {"type": "num"}
        elif isinstance(type_spec, list):
            return {"type": "option", "options": type_spec}
        else:
            return {"type": "str"}

    def _add_container(self, config):
        container = self.AttributeContainer(
            config, self.attribute.signal[config["name"]], self._main_widget
        )
        container.value_changed.connect(
            lambda val, name=config["name"]: self.value_changed.emit(name, val)
        )
        container.open_script_editor.connect(self.request_script_editor.emit)
        container.open_widget_editor.connect(self.open_widget_editor.emit)
        self._containers[config["name"]] = container
        self._vlayout.addWidget(container)

    def pack(self):
        values = {}
        for name, container in self._containers.items():
            values[name] = container.get_value()
        return (self._layer_type, values)

    def get_value(self, attr_name):
        if attr_name in self._containers:
            return self._containers[attr_name].get_value()
        return None

    def set_value(self, attr_name, value):
        if attr_name in self._containers:
            self._containers[attr_name].set_value(value)

    def get_all_values(self):
        return {name: c.get_value() for name, c in self._containers.items()}

    def connect_tip_signal(self, tip_bar):
        for container in self._containers.values():
            container.tip_signal.connect(tip_bar.set_tip)

class AttributePanal(StackWidget):
    summon_widget = pyqtSignal(object, object, object)  # (typ, pos, hash_id)
    delect_widget = pyqtSignal(object, object)
    send_data = pyqtSignal(object, object, object)
    request_script_editor = pyqtSignal(object)  # 轉發 container 的腳本編輯器請求
    open_widget_editor = pyqtSignal(
        object, object
    )  # 開啟 widget 子列表信號 (container, widget_data)

    def __init__(self, data=None, signal=None, tip_signal=None, parent=None):
        super().__init__(parent)
        self.override = OverrideWidget(
            "drop here\nset preset value", "img/edit/att_drag.png", self
        )
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.opened_widget=[]
        self.summon_widget.connect(self._on_summon_widget)
        self.tip_signal = tip_signal
        self._attribute_cache = {}  # {hash_id: 已生成的屬性列表}
        self._widget_views = {}  # {container_id: widget_view} 儲存每個 container 的 widget 視窗
        home=AttributeForm(getattr(components,"watchSetting"))
        self.addWidget(home,1)
        self.id_stack = [2]

    def go_back(self):
        self.opened_widget.pop()
        if self.opened_widget==[]:
            self.toggle_widget(1)
            return
        self.toggle_widget(self.opened_widget.pop())

    def go_home(self):
        self.toggle_widget(1)
        self.opened_widget=[]

    def toggle_widget(self,widget):
        if isinstance(widget,QWidget):
            super().setCurrentWidget(widget)
            return
        result=self.find(widget)
        if result:
            super().setCurrentWidget(result)
            return
        print(f"can't toggle to widget {widget}")

    def create_widget(self, att, name=None):
        if self.find(name):
            self.setCurrentWidget(self.find(name))
            return
        if name is None:
            name=self.get_hash_id()
        form = AttributeForm(att)
        # 連接 AttributeForm 的信號到 AttributePanal
        form.request_script_editor.connect(self.request_script_editor.emit)
        form.go_back.connect(self.go_back)
        form.go_home.connect(self.go_home)
        self.addWidget(form, name)
        
    def setCurrentIndex(self, index):
        super().setCurrentIndex(index)
        self.opened_widget.append(self.currentWidget())
        print(self.opened_widget)

    def setCurrentWidget(self, index):
        super().setCurrentWidget(index)
        self.opened_widget.append(self.currentWidget())
        print(self.opened_widget)

    def _on_summon_widget(self, typ, pos, hash_id):
        """處理 summon_widget 信號"""
        self.create_components(typ, pos, hash_id)

    def create_components(self, typ, pos=None, hash_id=None):
        """創建元件的屬性表單"""
        # 獲取或創建模板
        print(f"Debug: Trying to load component named '{typ}'")
        template = self.find(typ)
        if not template:
            # 第一次：從 components 模組獲取定義並創建模板
            component_def = getattr(components, typ, None)
            if component_def is None:
                print(f"Warning: Component '{typ}' not found")
                return
            template = AttributeForm(component_def)
            template.request_script_editor.connect(self.request_script_editor.emit)
            template.go_back.connect(self.go_back)
            template.go_home.connect(self.go_home)
            self.addWidget(template, typ, switch=False)

        # 從模板獲取資料
        layer_type = template._layer_type
        current_values = template.get_all_values()

        # 取得或生成 hash_id
        if hash_id is None or hash_id == 0:
            hash_id = self.get_hash_id()

        # 組建屬性列表
        att = [{"TYPE": layer_type}]
        for name, value in current_values.items():
            # 設定 X, Y 為滑鼠位置
            if name == "X" and pos is not None:
                att.append({name: pos[0]})
            elif name == "Y" and pos is not None:
                att.append({name: pos[1]})
            # 設定 Name 為 Layer + hash_id
            elif name == "Name":
                att.append({name: f"Layer{hash_id}"})
            else:
                att.append({name: value})

        # 創建新實例
        form = AttributeForm(att)
        form.go_back.connect(self.go_back)
        form.go_home.connect(self.go_home)
        form.request_script_editor.connect(self.request_script_editor.emit)
        self.addWidget(form, hash_id, switch=True)

        # 發送 hash_id, attribute, layer_type 給 WatchPreview
        self.send_data.emit(hash_id, form.get_attribute(), layer_type)

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
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """拖拽離開時重置"""
        self.is_drag_over = False
        self.override.show()

    def dropEvent(self, event):
        text = event.mimeData().text()
        print(text)
        self.create_widget(getattr(components, text), text)
        event.ignore()

    def required_visual_effects(self, event):
        return self.rect().center(), self.size()

class EditView(QWidget):
    exp_singal = pyqtSignal(object, object, object)
    summon_script_view = pyqtSignal(object, object)  # (edit_view, container)

    def __init__(self, parent=None, data=None, tip_signal=None):
        super().__init__(parent)
        if data is None:
            data = [""]
        self.data = data
        self.tip_signal = tip_signal
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.is_dragging = False
        self.id_stack = [1]
        self.set_ui()
        self.setStyleSheet(load_style())

    def set_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.explorer = Exploror(self.data, self.exp_singal)
        self.watch_preview = WatchPreview(self.data)

        component_related = QSplitter(Qt.Vertical)
        self.components = ComponentPanel(self.data)
        self.attribute = AttributePanal(self.data, self.tip_signal)
        self.drag_box = DragVisual(self)
        component_related.setObjectName("objectSplitter")
        component_related.setHandleWidth(2)
        component_related.addWidget(self.components)
        component_related.addWidget(self.attribute)
        component_related.setSizes([250, 250])

        main_layout.addWidget(self.explorer)
        main_layout.addWidget(self.watch_preview)
        main_layout.addWidget(component_related)

        # 安裝事件過濾器到所有可拖放區域
        self.explorer.installEventFilter(self)
        self.explorer.viewport().installEventFilter(self)
        self.watch_preview.installEventFilter(self)
        self.watch_preview.viewport().installEventFilter(self)
        self.components.installEventFilter(self)
        self.components.viewport().installEventFilter(self)
        self.attribute.installEventFilter(self)

        self.watch_preview.summon.connect(self.pre_call)
        self.components.button_trigger.connect(self.com_call)
        self.attribute.send_data.connect(self.att_call)
        # 連接腳本編輯器請求信號
        self.attribute.request_script_editor.connect(
            lambda container: self.summon_script_view.emit(self, container)
        )

    def delete_component(self, obj):
        self.id_stack.append(obj.hash_id)

    def att_call(self, hash_id, attribute, layer_type):
        self.watch_preview.receive.emit(hash_id, attribute, layer_type)

    def com_call(self, obj_type, data):
        if data == "drop":
            self.item_drop()
            return

    def pre_call(self, obj_type, pos, hash_id):
        if hash_id == 0:
            hash_id = self.get_hash_id()
        self.attribute.summon_widget.emit(obj_type, pos, hash_id)

    def get_hash_id(self):
        if self.id_stack[-1] is self.id_stack[0]:
            out = self.id_stack.pop()
            self.id_stack.append(out + 1)
            return out
        else:
            return self.id_stack.pop()

    def signal_manager(self, *state):
        if state[1] in ["drop", "copy"]:
            self.item_drop()
            return

    def show_all_overrides(self):
        """顯示所有 OverrideWidget"""
        self.explorer.override.show()
        self.watch_preview.override.show()
        self.components.override.show()
        self.attribute.override.show()

    def hide_all_overrides(self):
        """隱藏所有 OverrideWidget"""
        self.explorer.override.hide()
        self.watch_preview.override.hide()
        self.components.override.hide()
        self.attribute.override.hide()

    def _get_drop_target(self, watched):
        """取得拖放目標 widget（處理 viewport 的情況）"""
        # 如果 watched 是 viewport，返回其父 widget
        parent = watched.parent()
        if parent in [
            self.explorer,
            self.watch_preview,
            self.components,
            self.attribute,
        ]:
            return parent
        return watched

    def _get_target_widget_at_pos(self, global_pos):
        """根據全局座標取得對應的拖放目標 widget"""
        for widget in [
            self.explorer,
            self.watch_preview,
            self.components,
            self.attribute,
        ]:
            widget_rect = QRect(widget.mapToGlobal(QPoint(0, 0)), widget.size())
            if widget_rect.contains(global_pos):
                return widget
        return None

    def eventFilter(self, watched, event):
        target = self._get_drop_target(watched)

        if event.type() == QEvent.DragEnter:
            if not self.is_dragging:
                self.is_dragging = True
                self.show_all_overrides()
            if hasattr(target, "override"):
                target.override.hide()

        if event.type() == QEvent.DragMove:
            if hasattr(target, "required_visual_effects"):
                pos, size = target.required_visual_effects(event)
                pos = self.mapFromGlobal(target.mapToGlobal(pos))
                self.drag_box.change(pos, size)

        if event.type() == QEvent.DragLeave:
            # 檢查滑鼠是否真的離開了該元件的邊界
            cursor_pos = QCursor.pos()
            target_rect = QRect(target.mapToGlobal(QPoint(0, 0)), target.size())
            # 只有當滑鼠真正離開 target 邊界時才顯示 override
            if not target_rect.contains(cursor_pos) and hasattr(target, "override"):
                target.override.show()

        return False

    def dragEnterEvent(self, event):
        """處理拖曳進入 EditView 本身"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            if not self.is_dragging:
                self.is_dragging = True
                self.show_all_overrides()

    def dragMoveEvent(self, event):
        """處理拖曳在 EditView 移動"""
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """處理拖曳離開 EditView - 這是真正離開整個區域"""
        self.is_dragging = False
        self.hide_all_overrides()
        self.drag_box.hide()

    def item_drop(self):
        self.is_dragging = False
        self.hide_all_overrides()
        self.drag_box.hide()

    def dropEvent(self, event):
        """處理放下事件"""
        self.item_drop()
