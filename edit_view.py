import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QSplitter, QScrollArea, QSizePolicy, QPushButton,
                             QGridLayout, QTreeWidget, QTreeWidgetItem,
                             QStackedWidget, QListWidget, QListWidgetItem,
                             QLineEdit, QComboBox, QColorDialog)
from PyQt5.QtCore import Qt, QPoint, QMimeData, pyqtSignal, QSize, QThread, QTimer, QEvent, QRect, QPropertyAnimation, QEasingCurve, QObject
from PyQt5.QtGui import QPixmap, QIcon, QDrag, QCursor, QColor
from script_view import ScriptView
from common import FlowLayout, WatchFaceText, StackWidget
import components
from summon_obj import *

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
    cls.draged=False

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self,event):
        original_mouseMove(self,event)
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        # 检查移动距离是否超过启动拖拽的阈值
        if (event.pos() - self.drag_start_position).manhattanLength() < 5:
            return
        # 创建拖拽对象
        self.come_from=True
        drag = QDrag(self)
        mime_data = QMimeData()
        # 存储组件信息（tooltip）
        mime_data.setText(self.name)
        drag.setMimeData(mime_data)
        self.signal.emit(self.name,self.attributes)
        # 执行拖拽
        result=drag.exec_(Qt.CopyAction)
        if result is result:
            self.signal.emit(self.name,"drop")
        # 重置拖拽起始位置
        self.drag_start_position = None
        self.draged=True

    def mouseReleaseEvent(self, event):
        if self.draged is False:
            original_mousePress(self,event)
            self.draged=False
        original_mouseRelease(self,event)

    cls.mousePressEvent=mousePressEvent
    cls.mouseMoveEvent=mouseMoveEvent
    cls.mouseReleaseEvent=mouseReleaseEvent
    return cls

@Dragable
class ComponentButton(QPushButton):
    """組件按鈕類，支持拖拽"""
    def __init__(self, image_path, tooltip_text, signal,parent=None,name=None):
        super().__init__(parent)
        self.setObjectName("componentButton")
        self.setFixedSize(60, 60)
        self.setToolTip(tooltip_text)
        self.image_path = image_path
        self.name=tooltip_text.replace(' ', '_') if name is None else name
        self.signal=signal

        # 載入圖片並設置為按鈕圖示
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 等比例縮放圖片以適應按鈕
            scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(scaled_pixmap)
            self.setIcon(icon)
            self.setIconSize(scaled_pixmap.size())

    def get_attribute(self):
        return self.attributes

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if not hasattr(self,"attributes"):
            self.attributes=getattr(components,self.name)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not hasattr(self,"attributes"):
            self.attributes=getattr(components,self.name)
        self.signal.emit(self.name,self.attributes)

def _generate_tooltip(filename):
    """從文件名生成 tooltip 文字"""
    # 去除 btn_ 前綴和 .png 後綴
    name = filename.replace('btn_', '').replace('.png', '')
    # 將下劃線替換為空格
    name = name.replace('_', ' ')
    # 首字母大寫
    return name

def _create_component_buttons(self,signal,data=[""]):
    """創建組件按鈕"""
    # 搜索所有 btn_ 開頭的圖片
    image_folders = ['img/edit']
    button_data = []

    for folder in image_folders:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.startswith('btn_') and filename.endswith('.png'):
                    image_path = os.path.join(folder_path, filename)
                    # 生成 tooltip 文字
                    tooltip = _generate_tooltip(filename)
                    button_data.append((image_path, tooltip))

    return [ComponentButton(data[0], data[1], signal, self) for data in button_data]

class OverrideWidget(QWidget):
    def __init__(self, text, img_path, parent=None):
        super().__init__(parent)
        #self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        # 設定半透明背景
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('''
            background-color: rgba(255, 255, 255, 80);
            border: 3px solid #3d3d3d;
        ''')
        information_layout=QVBoxLayout(self)
        information_layout.setAlignment(Qt.AlignCenter)

        Indication=QPixmap(img_path)
        img=QLabel()
        img.setAlignment(Qt.AlignCenter)
        #img.setMaximumSize(100,100)
        img.setPixmap(Indication)
        img.setStyleSheet('''
            background-color: transparent;
            border: None;
        ''')
        information_layout.addWidget(img)

        self.information=QLabel()
        self.information.setAlignment(Qt.AlignCenter)
        self.information.setMaximumSize(200,50)
        self.information.setText(text)
        self.information.setStyleSheet('''
            background-color: transparent; color: #3d3d3d;
            font-weight:bold;
            border: None;
        ''')
        information_layout.addWidget(self.information)
        self.hide()

    def change_text(self,text):
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
        self.animation=False

        self.last_time=None

    def change(self, pos, size):
        # 設定目標 geometry
        pos = QPoint(pos.x() - size.width()//2, pos.y() - size.height()//2)
        target = QRect(pos, size)

        # 如果第一次，就直接設置
        if not self.isVisible():
            self.setGeometry(target)
            self.raise_()
            self.show()
            return
        
        if target==self.last_time:
            return
        self.last_time=target

        # 若動畫正在跑，要先停止
        if self.anim.state() == QPropertyAnimation.Running:
            self.anim.stop()

        length=pos-self.pos()
        if length.manhattanLength()>=20:
            self.animation=True 
        if size!=self.size(): 
            self.animation=True

        if self.animation==True:
            # 重新播放動畫
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target)
            self.anim.start()
            self.animation=False
        else:
            self.setGeometry(target)

class Exploror(QTreeWidget):
    def __init__(self,data=None, signal=None,parent=None):
        super().__init__(parent)
        self.setMaximumWidth(200)
        self.override=OverrideWidget("drop here\nadd new item","img/edit/exp_drag.png",self)
        self.setAcceptDrops(True)
        self.send_all=signal

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

class WatchPreview(QWidget):
    select=pyqtSignal(object)
    summon=pyqtSignal(object,object,object)
    receive=pyqtSignal(object,object)

    def __init__(self,data=None,parent=None):
        super().__init__(parent)
        self.scale=[]
        self.hash_table={}
        self.face_img=QPixmap("img/edit/watch_base.png")
        self.face=QLabel()
        self.face.setMinimumSize(200,200)
        self.setAcceptDrops(True)
        self.receive.connect(self.show_component)
        self.set_ui()

    def set_ui(self):
        face_layout=QHBoxLayout(self)
        self.setMinimumSize(face_layout.minimumSize())
        face_layout.setContentsMargins(20,20,20,20)
        face_layout.setAlignment(Qt.AlignCenter)
        face_layout.addWidget(self.face)
        self.override=OverrideWidget("drop here\nadd new item","img/edit/view_drag.png",self)

    def show_component(self,obj,hash_id):
        obj.setParent(self)
        obj.installEventFilter(self)
        self.hash_table[obj]=hash_id
        obj.show()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            self.select.emit(self.hash_table[watched])
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        """更新圖片大小，保持長寬比"""
        if self.face_img.isNull():
            return
        # 獲取當前 widget 的大小
        size = self.size()
        # 按照長寬比縮放圖片以適應 widget 大小
        scaled_pixmap = self.face_img.scaled(
            size-QSize(40,40),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.override.resize(self.size())
        self.face.setPixmap(scaled_pixmap)

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

    def dropEvent(self, event):
        self.summon.emit(event.mimeData().text(),event.pos(),0)
        self.override.hide()

    def required_visual_effects(self, event):
        return event.pos(), QSize(60, 60)

class ComponentPanel(QScrollArea):
    add_component=pyqtSignal(object,object)
    button_trigger=pyqtSignal(object,object)
    def __init__(self,data=None, signal=None,parent=None):
        super().__init__(parent)
        self.data=data
        self.setWidgetResizable(True)
        self.setObjectName("componentsScroll")
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizePolicy(
            QSizePolicy.Preferred,   # width
            QSizePolicy.Preferred    # height（非 Expanding）
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
        self.override = OverrideWidget("drop here\nadd new item", "img/edit/com_drag.png", self)
        
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
    
class AttributeLayout(QVBoxLayout):
    class Container(QWidget):
        """單個屬性容器 - 儲存並顯示一個 attribute 值"""
        tip_signal = pyqtSignal(str)  # 發送 description 到 TipBar
        value_changed = pyqtSignal(object)  # (name, value) 值變更信號
        open_script_editor = pyqtSignal(object)  # 開啟腳本編輯器信號（傳遞 container 自身）

        def __init__(self, attr_config, parent=None):
            super().__init__(parent)
            self.row_layout=QHBoxLayout(self)
            self.row_layout.setContentsMargins(0, 2, 0, 2)
            self.row_layout.setSpacing(8)
            self.attr_config = attr_config
            self.name = attr_config.get("name", "")
            self.attr_type = attr_config.get("type", "text")
            self.default = attr_config.get("default", "")
            self.description = attr_config.get("description", "")
            self.options = attr_config.get("options", [])
            self._value = self.default
            self._create_ui()

        def copy(self):
            return AttributeLayout.Container(self.attr_config)

        def _create_ui(self):
            self.left = QLabel(self.name)
            self.left.setObjectName("attrLabel")
            self.left.setFixedWidth(80)

            # 根據 type 建立對應 UI
            if self.attr_type == "text":
                self._create_text_ui()
            elif self.attr_type == "number":
                self._create_number_ui()
            elif self.attr_type == "option":
                self._create_option_ui()
            elif self.attr_type == "color":
                self._create_color_ui()
            else:
                self._create_text_ui()

            # 統一設定 right 控件的大小策略
            self.right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            self.row_layout.addWidget(self.left)
            self.row_layout.addWidget(self.right, 1)  # stretch factor = 1

        def _create_text_ui(self):
            self.right = QLineEdit()
            self.right.setObjectName("attrInput")
            self.right.setText(str(self.default))
            self.right.textChanged.connect(self._on_text_changed)
            self.right.setAcceptDrops(False)

        def _create_number_ui(self):
            self.right = QWidget()
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            self.input.setText(str(self.default))
            self.input.textChanged.connect(self._on_text_changed)
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

            self.script_btn = QPushButton(">_")
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
            # 禁用滾輪，避免意外改變選項
            self.right.wheelEvent = lambda e: e.ignore()

        def _create_color_ui(self):
            self.right = QWidget()
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.color_btn = QPushButton()
            self.color_btn.setObjectName("colorButton")
            self.color_btn.setFixedSize(50, 25)
            self._current_color = QColor(f"#{self.default}") if self.default else QColor("#ffffff")
            self._update_color_button()
            self.color_btn.clicked.connect(self._on_color_clicked)
            right_layout.addWidget(self.color_btn)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            self.input.setText(str(self.default))
            self.input.textChanged.connect(self._on_color_text_changed)
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

        def _update_color_button(self):
            self.color_btn.setStyleSheet(
                f"background-color: {self._current_color.name()}; border: 1px solid #4d4d4d;"
            )

        def _on_text_changed(self, text):
            self._value = text
            self.attr_config["default"]=text
            self.value_changed.emit(text)

        def _on_combo_changed(self, text):
            self._value = text
            self.attr_config["default"]=text
            self.value_changed.emit(text)

        def _on_color_clicked(self):
            color = QColorDialog.getColor(self._current_color, self, "選擇顏色")
            if color.isValid():
                self._current_color = color
                self._update_color_button()
                # 去除 # 符號，只保留 6 位色碼
                hex_color = color.name()[1:]
                self.input.setText(hex_color)
                self._value = hex_color
                self.value_changed.emit( hex_color)

        def _on_color_text_changed(self, text):
            self._value = text
            self.attr_config["default"]=text
            # 嘗試更新色塊
            try:
                color = QColor(f"#{text}" if not text.startswith("#") else text)
                if color.isValid():
                    self._current_color = color
                    self._update_color_button()
            except:
                pass
            self.value_changed.emit( text)

        def get_value(self):
            return self._value
        
        def valid(self,text):
            try:
                text=str(text)
            except:
                return self._value

            if text==self._value:
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
            elif self.attr_type == "number":
                self.input.setText(str(value))
            else:
                # text type - self.right is QLineEdit
                self.right.setText(str(value))

        def enterEvent(self, event):
            super().enterEvent(event)
            self.tip_signal.emit(self.description)

        def leaveEvent(self, event):
            super().leaveEvent(event)
            self.tip_signal.emit("")

    def __init__(self, componet_type , parent=None):
        super().__init__(parent)
        self.data={}
        self.component_type=componet_type
        self.setContentsMargins(10,20,10,20)
        self.setSpacing(0)
        self.item=[]
        
    def addWidget(self, widget):
        super().addWidget(widget)
        self.data[widget.attr_config["name"]]=widget.get_value()
        self.item.append(widget)

    def summon(self):
        new=components_factory(*self.pack())
        for obj in self.item:
            new.connect(obj.name,obj.value_changed,obj.set_value)
            obj.value_changed.emit(obj.get_value())
        return new

    def pack(self):
        return (self.component_type,self.data)

class AttributePanal(StackWidget):
    def_widget=pyqtSignal(object,object)
    summon_widget=pyqtSignal(object,object,object)
    delect_widget=pyqtSignal(object,object)
    send_obj=pyqtSignal(object,object)
    request_script_editor=pyqtSignal(object)  # 轉發 container 的腳本編輯器請求
    def __init__(self, data=None, signal=None, tip_signal=None, parent=None):
        super().__init__(parent)
        self.override=OverrideWidget("drop here\nset preset value","img/edit/att_drag.png",self)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.summon_widget.connect(self.copy_widget)
        self.def_widget.connect(self.create_widget)
        self.tip_signal=tip_signal
        self.addWidget(QWidget())

    def copy_widget(self,com_type,pos,hash_id):
        widget=self.find(hash_id)
        if widget:
            self.setCurrentWidget(widget)
            return
        copy=self.find(com_type)
        copy=copy.widget()
        new=QScrollArea()
        new.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        new.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        new.setWidgetResizable(True)
        new.setObjectName("attrScroll")
        container=QWidget()
        container.setObjectName("attrWidget")
        new.setWidget(container)
        attributes_layout=AttributeLayout(com_type,container)
        l=copy.layout()
        for idx in range(l.count()):
            item=l.itemAt(idx).widget()
            copy_item=item.copy()
            # 連接 number 類型的腳本編輯器信號
            if copy_item.attr_type == "number":
                copy_item.open_script_editor.connect(self.request_script_editor.emit)
            if copy_item.name=="x":
                copy_item.set_value(pos.x())
            if copy_item.name=="y":
                copy_item.set_value(pos.y())
            attributes_layout.addWidget(copy_item)
        self.addWidget(new,str(hash_id))
        new=attributes_layout.summon()

        self.send_obj.emit(new,hash_id)

    def create_widget(self,obj,data=None):
        widget=self.find(obj)
        if widget:
            return
        new=QScrollArea()
        new.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        new.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        new.setWidgetResizable(True)
        new.setObjectName("attrScroll")
        container=QWidget()
        container.setObjectName("attrWidget")
        new.setWidget(container)
        attributes_layout=AttributeLayout(obj,container)
        
        for attr_config in data:
            att=AttributeLayout.Container(attr_config)
            # 連接 number 類型的腳本編輯器信號
            if att.attr_type == "number":
                att.open_script_editor.connect(self.request_script_editor.emit)
            attributes_layout.addWidget(att)
        self.addWidget(new,obj,False)

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
        text=event.mimeData().text()
        widget=self.find(text)
        self.setCurrentWidget(widget)
        event.ignore()

    def required_visual_effects(self, event):
        return self.rect().center(), self.size()

class EditView(QWidget):
    exp_singal=pyqtSignal(object,object,object)
    summon_script_view=pyqtSignal(object,object)  # (edit_view, container)

    def __init__(self, parent=None, data=None, tip_signal=None):
        super().__init__(parent)
        if data is None:
            data=[""]
        self.data=data
        self.tip_signal = tip_signal
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.is_dragging = False
        self.id_stack=[1]
        self.set_ui()
        self.setStyleSheet(load_style())

    def set_ui(self):
        main_layout=QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.explorer=Exploror(self.data, self.exp_singal)
        self.watch_preview=WatchPreview(self.data)

        component_related=QSplitter(Qt.Vertical)
        self.components=ComponentPanel(self.data)
        self.attribute=AttributePanal(self.data, self.tip_signal)
        self.drag_box=DragVisual(self)
        component_related.setObjectName("objectSplitter")
        component_related.setHandleWidth(2)
        component_related.addWidget(self.components)
        component_related.addWidget(self.attribute)
        component_related.setSizes([250,250])

        main_layout.addWidget(self.explorer)
        main_layout.addWidget(self.watch_preview)
        main_layout.addWidget(component_related)

        # 安裝事件過濾器到所有可拖放區域
        self.explorer.installEventFilter(self)
        self.explorer.viewport().installEventFilter(self)
        self.watch_preview.installEventFilter(self)
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

    def get_hash_id(self):
        if self.id_stack[-1] is self.id_stack[0]:
            out=self.id_stack.pop()
            self.id_stack.append(out+1)
            return out
        else:
            return self.id_stack.pop()
        
    def delete_component(self,obj):
        self.id_stack.append(obj.hash_id)

    def att_call(self,obj,hash_id):
        self.watch_preview.receive.emit(obj,hash_id)

    def com_call(self,obj_type,data):
        if data=="drop":
            self.item_drop()
            return
        self.attribute.def_widget.emit(obj_type,data)

    def pre_call(self,obj_type,data,hash_id):
        if hash_id==0:
            hash_id=self.get_hash_id()
        self.attribute.summon_widget.emit(obj_type,data,hash_id)

    def signal_manager(self,*state):
        if state[1] in ["drop","copy"]:
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
        if parent in [self.explorer, self.components, self.attribute]:
            return parent
        return watched

    def _get_target_widget_at_pos(self, global_pos):
        """根據全局座標取得對應的拖放目標 widget"""
        for widget in [self.explorer, self.watch_preview, self.components, self.attribute]:
            widget_rect = QRect(
                widget.mapToGlobal(QPoint(0, 0)),
                widget.size()
            )
            if widget_rect.contains(global_pos):
                return widget
        return None

    def eventFilter(self, watched, event):
        target = self._get_drop_target(watched)

        if event.type() == QEvent.DragEnter:
            if not self.is_dragging:
                self.is_dragging = True
                self.show_all_overrides()
            if hasattr(target, 'override'):
                target.override.hide()

        if event.type() == QEvent.DragMove:
            if hasattr(target, 'required_visual_effects'):
                pos, size = target.required_visual_effects(event)
                pos = self.mapFromGlobal(target.mapToGlobal(pos))
                self.drag_box.change(pos, size)

        if event.type() == QEvent.DragLeave:
            # 檢查滑鼠是否真的離開了該元件的邊界
            cursor_pos = QCursor.pos()
            target_rect = QRect(
                target.mapToGlobal(QPoint(0, 0)),
                target.size()
            )
            # 只有當滑鼠真正離開 target 邊界時才顯示 override
            if not target_rect.contains(cursor_pos) and hasattr(target, 'override'):
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