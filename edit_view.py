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
    QSlider,
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
import re

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
        # 执行拖拽
        result = drag.exec_(Qt.CopyAction)
        if result is result:
            self.signal.emit("drop")
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

class Exploror(QWidget):
    def __init__(self, data=None, id_stack=None, signal=None, parent=None):
        super().__init__(parent)
        self.setObjectName("explorer")
        self._vlayout=QVBoxLayout(self)
        self._vlayout.setContentsMargins(0,5,7,0)
        hlayout=QHBoxLayout(self)
        sort_label=QLabel("      Sort by")
        sort_label.setObjectName("explorerSortLabel")
        self.sort_option=QComboBox()
        self.sort_option.setObjectName("explorerCombo")
        self.sort_option.addItems(["level","name","layer"])
        hlayout.addWidget(sort_label,2)
        hlayout.addWidget(self.sort_option,3)
        self._vlayout.addLayout(hlayout,1)
        self.tree=QTreeWidget()
        self.tree.setObjectName("explorerTree")
        self.setMaximumWidth(300)
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Name","Layer","     "])
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._vlayout.addWidget(self.tree,19)
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
    receive = pyqtSignal(object,object,object)

    # 場景固定大小 (錶面尺寸)
    SCENE_SIZE = 454

    def __init__(self, data=None, id_stack=None, parent=None):
        super().__init__(parent)
        self.scale = []
        self.hash_table = {}
        self.sence = QGraphicsScene()
        # 設定固定的場景範圍
        self.sence.setSceneRect(-self.SCENE_SIZE/2, -self.SCENE_SIZE/2, self.SCENE_SIZE, self.SCENE_SIZE)
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
            -diameter/2,
            -diameter/2,
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

    def summon_component(self, layer_type, signal_dict, hash_id):
        """根據屬性和圖層類型創建元件並顯示在預覽區"""
        # 使用 summon_obj 的 create_layer 函數創建對應的圖層
        layer = summon_obj.create_layer(layer_type, signal_dict,hash_id,self.sence)
        # 儲存到 hash_table
        self.hash_table[hash_id] = layer

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            self.select.emit(self.hash_table[watched])
        return False

    def dragEnterEvent(self, event):
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
        if event.mimeData().hasText():
            # 將視窗座標轉換為場景座標，並計算相對於中心的位置
            scene_pos = self.mapToScene(event.pos())
            x = int(scene_pos.x())
            y = int(scene_pos.y())
            self.summon.emit(event.mimeData().text(), (x, y), 0)
            event.acceptProposedAction()
        self.override.hide()

    def required_visual_effects(self, event):
        return event.pos(), QSize(60, 60)


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

class AttributeForm(QScrollArea):
    """Scrollable form containing multiple attribute containers"""

    class AttributeContainer(QWidget):
        """單個屬性容器 - 儲存並顯示一個 attribute 值"""

        tip_signal = pyqtSignal(str)
        value_changed = pyqtSignal(object)
        open_script_editor = pyqtSignal(object)
        open_widget_editor = pyqtSignal()

        def __init__(self, title,value,description,typ,signal, parent=None):
            super().__init__(parent)
            self.name = title
            self.attr_type = typ
            self.default = value
            self.description = description
            self.options = typ
            self.signal = signal
            self._value = self.default
            self._create_ui()

        def _create_ui(self):
            self.left = QLabel(self.name)
            self.left.setObjectName("attrLabel")

            if self.attr_type == "color":
                self._create_color_ui()
            elif self.attr_type == "widget":
                self._create_widget_ui()
            elif self.attr_type == "bool":
                self._create_bool_ui()
            elif self.attr_type == "file":
                self._create_file_ui()
            elif self.attr_type == "font" or isinstance(self.attr_type,list):
                self._create_option_ui()
            elif isinstance(self.attr_type,tuple) and self.attr_type[2]==1:
                self._create_int_ui()
            elif isinstance(self.attr_type,tuple) and self.attr_type[2]==0:
                self._create_num_ui()
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
            self.signal.connect(self.set_value)

        def _create_str_ui(self):
            if self.name in ["Text","Script"]:
                self._create_num_ui()
                return
            self.right = QLineEdit()
            self.right.setObjectName("attrInput")
            self.right.textChanged.connect(self._on_text_changed)
            if self.name=="Name":
                self.right.editingFinished.connect(lambda:self.value_processing(self.right.text()))
            else:
                self.right.textChanged.connect(self.value_processing)
            self.right.setText(str(self.default))
            self.right.setAcceptDrops(False)

        def _create_int_ui(self):
            if self.attr_type[1]-self.attr_type[0]<=100:
                self.right = QWidget()
                right_layout = QHBoxLayout(self.right)
                slide = QSlider()
                slide.setRange(self.attr_type[0],self.attr_type[1])
                right_layout.addWidget(slide,4)
                self.input=QLineEdit()
                right_layout.addWidget(slide,1)
                slide.valueChanged.connect(lambda text:self.input.setText(str(text)))
                def textEdit(text):
                    try:
                        slide.setValue(int(text))
                    except:
                        pass
                self.input.textEdited.connect(textEdit)
                self.input.textChanged.connect(self._on_text_changed)
                self.input.textChanged.connect(self.value_processing)
                slide.setValue(int(self.default))
                self.input.setAcceptDrops(False)
                return
            self.right = QLineEdit()
            self.right.setObjectName("attrInput")
            self.right.textChanged.connect(self._on_text_changed)
            self.right.textChanged.connect(self.value_processing)
            self.right.setText(str(self.default))
            self.right.setAcceptDrops(False)

        def _create_num_ui(self):
            self.right = QWidget()
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            self.input.textChanged.connect(self._on_text_changed)
            self.input.textChanged.connect(self.value_processing)
            self.input.setText(str(self.default))
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

            self.script_btn = QPushButton("_<")
            self.script_btn.setObjectName("scriptButton")
            self.script_btn.setFixedSize(30, 25)
            self.script_btn.clicked.connect(lambda: self.open_script_editor.emit(self))
            right_layout.addWidget(self.script_btn)

        def _create_option_ui(self):
            if self.attr_type == "font":
                font_manager = FontManager()
                self.options = font_manager.get_available_fonts()
                if not self.options:
                    self.options = ["Arial"]
            self.right = QComboBox()
            self.right.setObjectName("attrCombo")
            self.right.addItems([str(opt) for opt in self.options])
            index = self.right.findText(str(self.default))
            self.right.currentTextChanged.connect(self._on_combo_changed)
            self.right.currentTextChanged.connect(self.value_processing)
            if index >= 0:
                self.right.setCurrentIndex(index)
                self.signal.emit(str(self.default))
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
            self.input.textChanged.connect(self._on_color_text_changed)
            self.input.textChanged.connect(self.value_processing)
            self.input.setText(str(self.default))
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

        def _create_widget_ui(self):
            self.right = QPushButton()
            self.right.setObjectName("expandButton")
            self.right.clicked.connect(self.open_widget_editor.emit)
            self.signal.connect(self.right.setText)

        def _create_bool_ui(self):
            self.right = QRadioButton()
            self.right.setObjectName("attrCombo")
            self.right.clicked.connect(self._on_bool_changed)
            self.right.clicked.connect(self.value_processing)
            self.right.setChecked(self.default)

        def _on_bool_changed(self, text):
            self._value = text == "True"
            self.default = self._value
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
                self.default = file_path
                self._update_file_button_text()
                self.value_changed.emit(file_path)
                self.value_processing(file_path)

        def _update_color_button(self):
            self.color_btn.setStyleSheet(
                f"background-color: {self._current_color.name()}; border: 1px solid #4d4d4d;"
            )

        def _on_text_changed(self, text):
            self._value = text
            self.default = text
            self.value_changed.emit(text)

        def _on_combo_changed(self, text):
            self._value = text
            self.default = text
            self.value_changed.emit(text)

        def _on_color_clicked(self):
            color = QColorDialog.getColor(self._current_color, self, "choose color")
            if color.isValid():
                self._current_color = color
                self._update_color_button()
                hex_color = color.name()[1:]
                self.input.setText(hex_color)
                self._value = hex_color
                self.value_changed.emit(hex_color)

        def _on_color_text_changed(self, text):
            self._value = text
            self.default = text
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
        
        def value_processing(self,value):
            try:
                if self.attr_type == "bool":
                    value=bool(value)
                elif isinstance(self.attr_type,tuple) and self.attr_type[2]==1:
                    value=int(value)
                elif isinstance(self.attr_type,tuple) and self.attr_type[2]==0:
                    value=float(value)
                    if self.name=="Rotation":
                        value=value%360
                    value=min(value,self.attr_type[1])
                    value=max(value,self.attr_type[0])
                    value=float(value)
                else:
                    value=str(value)
                self.signal.emit(value)
            except:
                pass
            

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
            print(value,self.attr_type,self.name)
            if isinstance(self.attr_type,list) or self.attr_type=="font":
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
            elif isinstance(self.attr_type,tuple):
                self.input.setText(str(value))
            elif self.attr_type == "widget":
                self._value = None
            elif self.attr_type == "bool":
                self.right.setChecked(value)
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
    open_widget_editor = pyqtSignal()
    value_changed = pyqtSignal(str, object)
    go_back=pyqtSignal()
    go_home=pyqtSignal()
    name_disturbute={}

    def __init__(self, attribute_list, name_distrbute, parent=None):
        super().__init__(parent)
        self._setup_scroll_area()
        self._containers = {}
        self._layer_type = attribute_list[0]["TYPE"]
        self.name_distrbute=name_distrbute
        self.child_widget=None
        if attribute_list[0]["TYPE"]!="baseLayer":
            self.back_container(attribute_list[0]["TYPE"])

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

    def back_container(self,typ):
        import components.common as common_defs
        hlayout=QHBoxLayout()
        back=QPushButton("< Back")
        home=QPushButton("Home")
        hlayout.addWidget(back)
        if typ!="animationWidget":
            layer_combo=QComboBox()
            layer_combo.setObjectName("attrCombo")
            layer_names=[name for name in common_defs.__all__ if name!="baseLayer" and name!="animationWidget"]
            layer_combo.addItems(layer_names)
            if self._layer_type and self._layer_type in layer_names:
                layer_combo.setCurrentText(self._layer_type)
            hlayout.addWidget(layer_combo)
        else:
            hlayout.addStretch()
        hlayout.addWidget(home)
        back.clicked.connect(self.go_back.emit)
        home.clicked.connect(self.go_home.emit)
        self._vlayout.addLayout(hlayout)

    def add_container(self, title, value, description, typ, signal):
        container = self.AttributeContainer(title,value,description,typ,signal)
        container.open_script_editor.connect(self.request_script_editor.emit)
        container.open_widget_editor.connect(self.open_widget_editor.emit)
        self._containers[title] = container
        if title!="Display":
            self._vlayout.addWidget(container)
        
        if title == "Name":
            # 【關鍵修改 1】初始化時先預設為 None，並主動呼叫一次改名驗證，確保拖入新元件時名稱就不會重複
            container.last_valid_name = None 
            self.rename_valid(value, container)
            
            # 綁定使用者修改名稱的信號
            signal.connect(lambda text: self.rename_valid(text, container))

    def rename_valid(self, new_name, container):
        old_name = getattr(container, "last_valid_name", None)

        if old_name == new_name:
            return

        if old_name and old_name in self.name_distrbute:
            del self.name_distrbute[old_name]

        final_name = new_name
        base_name = re.sub(r' \(\d+\)$', '', new_name)
        counter = self.name_distrbute[final_name] if final_name in self.name_distrbute else 1

        while final_name in self.name_distrbute:
            final_name = f"{base_name} ({counter})"
            counter += 1

        self.name_distrbute[final_name] = counter
        container.last_valid_name = final_name

        if final_name != new_name:
            container.set_value(final_name)

    def pack(self):
        values = []
        values.append({"TYPE":self._layer_type})
        for name, container in self._containers.items():
            item={name:container.get_value(),"description":container.description}
            if item[name] is None:
                item[name]=self.child_widget.pack()
            values.append(item)
        return values

    def get_value(self, attr_name):
        if attr_name in self._containers:
            return self._containers[attr_name].get_value()
        return None

    def set_value(self, attr_name, value):
        if attr_name in self._containers:
            self._containers[attr_name].set_value(value)

    def get_all_values(self):
        return {name: c.get_value() for name, c in self._containers.items()}

    def connect_tip_signal(self,tip_signal):
        for container in self._containers.values():
            container.tip_signal.connect(tip_signal.emit)

    def get_signal(self,name):
        return self._containers[name].signal

class AttributePanal(StackWidget):
    summon_widget = pyqtSignal(list)  # (typ, pos, hash_id)
    delect_widget = pyqtSignal(object, object)
    send_obj = pyqtSignal(object,object,object)
    request_script_editor = pyqtSignal(object)  # 轉發 container 的腳本編輯器請求
    open_widget_editor = pyqtSignal()

    def __init__(self, data=None, id_stack=None, tip_signal=None, parent=None):
        super().__init__(parent)
        self.override = OverrideWidget(
            "drop here\nset preset value", "img/edit/att_drag.png", self
        )
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.summon_widget.connect(self._on_summon_widget)
        self.tip_signal = tip_signal
        self._attribute_cache = {}  # {hash_id: 已生成的屬性列表}
        self._widget_views = {}  # {container_id: widget_view} 儲存每個 container 的 widget 視窗
        self.opened_widget=[]
        self.name={}
        if id_stack is None:
            self.id_stack = [2]
        else:
            self.id_stack =id_stack
        self.addWidget(getattr(components,"watchSetting"),1)
        self.opened_widget=[self.currentWidget()]
    
    def get_hash_id(self):
        if self.id_stack[-1] is self.id_stack[0]:
            out = self.id_stack.pop()
            self.id_stack.append(out + 1)
            return out
        else:
            return self.id_stack.pop()

    def addWidget(self, att_list, id=None, create=False, switch=True):
        widget=AttributeForm(att_list,self.name,self)
        layer_type=att_list.pop(0)["TYPE"]
        layer_def=getattr(components,layer_type,{})
        signal_dict={}

        for att in att_list:
            signal=summon_obj.Signal()
            title,value=list(att.items())[0]
            signal_dict[title]=signal
            description=att["description"]
            typ=layer_def.get(title,[])
            if typ=="widget":
                display=value[1]["Display"]
                widget_id=self.get_hash_id()
                signal_dict.update(self.addWidget(value,widget_id,False,False))
                widget.child_widget = self.find(widget_id)
                signal = widget.child_widget.get_signal(display)
                widget.open_widget_editor.connect(lambda:self.setCurrentWidget(self.find(widget_id)))
            widget.add_container(title,value,description,typ,signal)

        if self.tip_signal is not None:
            widget.connect_tip_signal(self.tip_signal)
        widget.request_script_editor.connect(self.request_script_editor.emit)
        widget.go_back.connect(self.go_back)
        widget.go_home.connect(self.go_home)
        if id is None:
            id=self.get_hash_id()
        if create:
            self.send_obj.emit(layer_type,signal_dict,id)
        super().addWidget(widget, id, switch)
        return signal_dict

    def go_back(self):
        self.opened_widget.pop()
        if self.opened_widget==[]:
            self.toggle_widget(1)
            return
        self.toggle_widget(self.opened_widget[-1])
        print(self.opened_widget)

    def go_home(self):
        self.toggle_widget(1)
        self.opened_widget=[self.find(1)]

    def toggle_widget(self,widget):
        if isinstance(widget,QWidget):
            super().setCurrentWidget(widget)
            return
        result=self.find(widget)
        if result:
            super().setCurrentWidget(result)
            return
        print(f"can't toggle to widget {widget}")

    def setCurrentIndex(self, index):
        super().setCurrentIndex(index)
        if len(self.opened_widget)==0 or not self.opened_widget[-1] is self.currentWidget():
            self.opened_widget.append(self.currentWidget())

    def setCurrentWidget(self, index):
        super().setCurrentWidget(index)
        if len(self.opened_widget)==0 or not self.opened_widget[-1] is self.currentWidget():
            self.opened_widget.append(self.currentWidget())

    def _on_summon_widget(self, args):
        """處理 summon_widget 信號"""
        while len(args)<3:
            args.append(None)
        args=tuple(args)
        typ, pos, hash_id=args
        try:
            att_list=self.find(typ).pack()
        except AttributeError:
            att_list=getattr(components,typ)
        if pos is not None:
            for att in att_list:
                if "X" in att: att["X"]=pos[0]
                if "Y" in att: att["Y"]=pos[1] 
        if hash_id is None:
            hash_id=self.get_hash_id()
        self.addWidget(att_list,hash_id,True,True)

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
        self.addWidget(getattr(components, text), text)
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
        self.id_stack = [2]
        self.set_ui()
        self.setStyleSheet(load_style())

    def set_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.explorer = Exploror(self.data, self.id_stack, self.exp_singal)
        self.watch_preview = WatchPreview(self.data, self.id_stack)

        component_related = QSplitter(Qt.Vertical)
        self.components = ComponentPanel(self.data)
        self.attribute = AttributePanal(self.data, self.id_stack, self.tip_signal)
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
        self.explorer.installEventFilter(self)
        self.watch_preview.installEventFilter(self)
        self.watch_preview.viewport().installEventFilter(self)
        self.components.installEventFilter(self)
        self.components.viewport().installEventFilter(self)
        self.attribute.installEventFilter(self)

        self.watch_preview.summon.connect(self.pre_call)
        self.components.button_trigger.connect(self.com_call)
        self.attribute.send_obj.connect(self.att_call)
        # 連接腳本編輯器請求信號
        self.attribute.request_script_editor.connect(
            lambda container: self.summon_script_view.emit(self, container)
        )

    def delete_component(self, obj):
        self.id_stack.append(obj.hash_id)

    def att_call(self, *args):
        self.watch_preview.receive.emit(*args)

    def com_call(self, data):
        if data == "drop":
            self.item_drop()
            return
        self.attribute.summon_widget.connect([data])

    def pre_call(self, obj_type, pos, hash_id):
        if hash_id == 0:
            hash_id = self.get_hash_id()
        self.attribute.summon_widget.emit([obj_type, pos, hash_id])

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


#TODO:
#檔案總管排序
#檔案總管圖層管理