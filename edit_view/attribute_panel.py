import os
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QPushButton,
    QRadioButton,
    QLineEdit,
    QComboBox,
    QColorDialog,
    QFileDialog,
    QSlider,
    QUndoCommand
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
)
from common import StackWidget, FontManager, UndoGroupStack
import components
import edit_view.preview_obj as preview_obj
import re
from edit_view.drag_effect import *

class ContainerValueChange(QUndoCommand):
    def __init__(self,container,new_value,old_value):
        super().__init__()
        self.container = container
        self.new_value = new_value
        self.old_value = old_value

    def redo(self):
        self.container.set_value(self.new_value,False)

    def undo(self):
        self.container.set_value(self.old_value,False)

    def __del__(self):
        pass

class AttributeForm(QScrollArea):
    """Scrollable form containing multiple attribute containers"""

    class AttributeContainer(QWidget):
        """單個屬性容器 - 儲存並顯示一個 attribute 值"""

        tip_signal = pyqtSignal(str)
        value_changed = pyqtSignal(object)
        open_script_editor = pyqtSignal(object)
        open_widget_editor = pyqtSignal()

        def __init__(self, title, value, description, typ, signal:pyqtSignal, parent=None):
            super().__init__(parent)
            self.name = title
            self.attr_type = typ
            self.default = value
            self.description = description
            self.options = typ
            self.signal = signal
            self._value = self.default
            self.edit_finish=True
            self.undo_stack=None
            self._create_ui()

        def _create_ui(self):
            self.left = QLabel(self.name)
            self.left.setObjectName("attrLabel")

            self.right=QWidget()
            self.signal.connect(self.set_value)
            if self.attr_type == "color":
                self._create_color_ui()
            elif self.attr_type == "widget":
                self._create_widget_ui()
            elif self.attr_type == "bool":
                self._create_bool_ui()
            elif self.attr_type == "file":
                self._create_file_ui()
            elif self.attr_type == "font" or isinstance(self.attr_type, list):
                self._create_option_ui()
            elif isinstance(self.attr_type, tuple) and self.attr_type[2] == 1:
                self._create_int_ui()
            elif isinstance(self.attr_type, tuple) and self.attr_type[2] == 0:
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

        def _create_str_ui(self):
            if self.name in ["Text", "Script"]:
                self._create_num_ui()
                return
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QLineEdit()
            right_layout.addWidget(self.input)
            self.input.setObjectName("attrInput")
            if self.name != "Name":
                self.input.textChanged.connect(self.value_processing)
            self.input.editingFinished.connect(
                lambda: self.value_processing(self.input.text())
            )
            self.input.setText(str(self.default))
            self.signal.emit(self.input.text())
            self.input.setAcceptDrops(False)

        def _create_int_ui(self):
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            right_layout.addWidget(self.input)
            self.input.textChanged.connect(self.value_processing)
            self.input.setText(str(self.default))
            self.input.setAcceptDrops(False)

        def _create_num_ui(self):
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)

            self.input = QLineEdit()
            self.input.setObjectName("attrInput")
            
            self.input.textChanged.connect(self.value_processing)
            self.input.editingFinished.connect(
                lambda: self.value_processing(self.input.text())
            )
            self.input.setText(str(self.default))
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input,1)

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
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QComboBox()
            right_layout.addWidget(self.input)
            self.input.setObjectName("attrCombo")
            self.input.addItems([str(opt) for opt in self.options])
            index = self.input.findText(str(self.default))
            self.input.currentTextChanged.connect(lambda value:self.value_processing(value))
            if index >= 0:
                self.input.setCurrentIndex(index)
                self.signal.emit(str(self.default))
            self.input.wheelEvent = lambda e: e.ignore()

        def _create_color_ui(self):
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
            self.input.editingFinished.connect(
                lambda: self.value_processing(self.input.text())
            )
            self.input.setText(str(self.default))
            self.input.setAcceptDrops(False)
            right_layout.addWidget(self.input, 1)

        def _create_widget_ui(self):
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QPushButton()
            right_layout.addWidget(self.input)
            self.input.setObjectName("expandButton")
            self.input.clicked.connect(self.open_widget_editor.emit)
            self.signal.connect(self.input.setText)

        def _create_bool_ui(self):
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QRadioButton()
            right_layout.addWidget(self.input)
            self.input.setObjectName("attrCombo")
            self.input.clicked.connect(lambda value:self.value_processing(value))
            self.input.setChecked(self.default)

        def _create_file_ui(self):
            right_layout = QHBoxLayout(self.right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(4)
            self.input = QPushButton()
            right_layout.addWidget(self.input)
            self.input.setObjectName("fileButton")
            self._update_file_button_text()
            self.input.clicked.connect(self._on_file_clicked)

        def _update_file_button_text(self):
            """更新檔案按鈕的顯示文字"""
            if self._value and self._value != "":
                # 顯示檔案名稱（不含路徑）
                filename = os.path.basename(str(self._value))
                self.input.setText(filename)
            else:
                self.input.setText("None")

        def _on_file_clicked(self):
            """開啟檔案選擇對話框"""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "選擇檔案",
                "",
                "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.bmp);;3D Models (*.obj *.gltf *.glb)",
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

        def _on_color_clicked(self):
            color = QColorDialog.getColor(self._current_color, self, "choose color")
            if color.isValid():
                self._current_color = color
                hex_color = color.name()[1:]
                self.input.setText(hex_color)
                self._value = hex_color

        def _on_color_text_changed(self, text):
            try:
                color = QColor(f"#{text}" if not text.startswith("#") else text)
                if color.isValid():
                    self.value_processing(text if not text.startswith("#") else text[1:])
                    self._current_color = color
                    self._update_color_button()
            except:
                pass

        def get_value(self):
            return self._value

        def value_processing(self, value, edit_finish=None):
            if isinstance(self.input,QLineEdit):
                self.edit_finish=not self.input.hasFocus()
            if edit_finish is not None:
                self.edit_finish=edit_finish
            try:
                if self.attr_type == "bool":
                    value = bool(value)
                elif isinstance(self.attr_type, tuple) and self.attr_type[2] == 1:
                    value = float(value)
                    value = int(value)
                elif isinstance(self.attr_type, tuple) and self.attr_type[2] == 0:
                    value = float(value)
                    if self.name == "Rotation":
                        value = value % 360
                    value = min(value, self.attr_type[1])
                    value = max(value, self.attr_type[0])
                    value = float(value)
                else:
                    value = str(value)
                self.signal.emit(value)
            except:
                if self.edit_finish:
                    self.set_value(self._value)

        def is_valid(self, value):
            if isinstance(self.attr_type, tuple):
                try:
                    value=float(value)
                    text=re.sub(r"(\.\d*?[1-9])0+$|\.0+(?!\d)$","",str(value))
                    if text==self.input.text():                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                        return self._value
                    return text
                except:
                    return self._value
            if value==self._value:
                return self._value
            return value
            
        def set_value(self, value, push_undo_command=True):
            text=self.is_valid(value)
            if (not self.edit_finish) or (self._value == text):
                return
            if push_undo_command:
                self.push_undo_command(value,self._value)
            self._value = value
            if self.attr_type == "bool":
                self.input.setChecked(value)
                return
            if isinstance(self.attr_type, list) or self.attr_type == "font":
                index = self.input.findText(text)
                if index >= 0:
                    self.input.setCurrentIndex(index)
            elif self.attr_type == "widget": self._value=None
            elif self.attr_type == "file": self._update_file_button_text()
            else: self.input.setText(text)

        def set_undo_stack(self,stack):
            self.undo_stack=stack

        def push_undo_command(self,value,old_value):
            command=ContainerValueChange(self,value,old_value)
            try: 
                self.undo_stack.push(command)
            except: pass

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
    go_back = pyqtSignal()
    go_home = pyqtSignal()
    name_disturbute = {}

    def __init__(self, undo_stack,attribute_list,  parent=None):
        super().__init__(parent)
        self._setup_scroll_area()
        self._containers = {}
        self._layer_type = attribute_list[0]["TYPE"]
        self.child_widget = None
        self.undo_stack=undo_stack
        if attribute_list[0]["TYPE"] != "baseLayer":
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

    def back_container(self, typ):
        hlayout = QHBoxLayout()
        back = QPushButton("< Back")
        home = QPushButton("Home")
        hlayout.addWidget(back)
        hlayout.addStretch(1)
        hlayout.addWidget(home)
        back.clicked.connect(self.go_back.emit)
        home.clicked.connect(self.go_home.emit)
        self._vlayout.addLayout(hlayout)

    def add_container(self, title, value, description, typ, signal):
        container = self.AttributeContainer(title, value, description, typ, signal, self)
        container.set_undo_stack(self.undo_stack)
        container.open_script_editor.connect(self.request_script_editor.emit)
        container.open_widget_editor.connect(self.open_widget_editor.emit)
        self._containers[title] = container
        if title != "Button display":
            self._vlayout.addWidget(container)
            return
        container.hide()

    def pack(self):
        values = []
        values.append({"TYPE": self._layer_type})
        for name, container in self._containers.items():
            item = {name: container.get_value(), "description": container.description}
            if item[name] is None:
                item[name] = self.child_widget.pack()
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

    def connect_tip_signal(self, tip_signal):
        for container in self._containers.values():
            container.tip_signal.connect(tip_signal.emit)

    def get_signal(self, name):
        return self._containers[name].signal

class AttributePanal(StackWidget):
    summon_widget = pyqtSignal(list)  # (typ, pos, hash_id)
    delect_widget = pyqtSignal(object, object)
    send_obj = pyqtSignal(object, object, object)
    request_script_editor = pyqtSignal(object)  # 轉發 container 的腳本編輯器請求
    open_widget_editor = pyqtSignal()

    def __init__(self, undo_stack :UndoGroupStack|None=None, id_stack=None, tip_signal=None, parent=None):
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
        self.opened_widget = []
        if id_stack is None:
            self.id_stack = [2]
        else:
            self.id_stack = id_stack
        self.undo_stack=undo_stack
        self.addWidget(getattr(components, "watchSetting"), 1,False,True,False)
        self.opened_widget = [self.currentWidget()]
        self.del_widget=[]

    def get_hash_id(self):
        if self.id_stack[-1] is self.id_stack[0]:
            out = self.id_stack.pop()
            self.id_stack.append(out + 1)
            return out
        else:
            return self.id_stack.pop()

    def addWidget(self, att_list, id=None, create=False, switch=True, push_command=True):
        if self.find(id):
            return super().addWidget(widget, id, switch)
        widget = AttributeForm(self.undo_stack,att_list, self)
        layer_type = att_list.pop(0)["TYPE"]
        layer_def = getattr(components, layer_type, {})
        signal_dict = {}

        if id is None:
            id = self.get_hash_id()
        if push_command:
            self.undo_stack.beginMacro("add widget and layer")
            self.undo_command(widget,id,switch)
        else:
            super().addWidget(widget,id,switch)

        for att in att_list:
            signal = preview_obj.Signal()
            title, value = list(att.items())[0]
            signal_dict[title] = signal
            description = att["description"]
            typ = layer_def.get(title, [])
            if typ == "widget":
                display = value[1]["Button display"]
                widget_id = self.get_hash_id()
                signal_dict.update(self.addWidget(value, widget_id, False, False))
                self.undo_stack.endMacro()
                widget.child_widget = self.find(widget_id)
                signal = widget.child_widget.get_signal(display)
                widget.open_widget_editor.connect(
                    lambda: self.setCurrentWidget(self.find(widget_id))
                )
            widget.add_container(title, value, description, typ, signal)

        if self.tip_signal is not None:
            widget.connect_tip_signal(self.tip_signal)
        widget.request_script_editor.connect(self.request_script_editor.emit)
        widget.go_back.connect(self.go_back)
        widget.go_home.connect(self.go_home)
        
        if create:
            self.send_obj.emit(layer_type, signal_dict, id)
            print("end")
            self.undo_stack.endMacro()
        return signal_dict
    
    def removeWidget(self, target):
        for idx in range(len(self.opened_widget)):
            if self.opened_widget[idx] is target:
                del self.opened_widget[idx]
        return super().removeWidget(target)
    
    def undo_command(self,widget,id,switch):
            command=AddWidget(widget,self,id,switch)
            self.undo_stack.push(command)

    def go_back(self):
        self.opened_widget.pop()
        while self.opened_widget[-1] in self.del_widget:
            self.opened_widget.pop()
        if self.opened_widget == []:
            self.toggle_widget(1)
            return
        self.toggle_widget(self.opened_widget[-1])

    def go_home(self):
        self.toggle_widget(1)
        self.opened_widget = [self.find(1)]

    def toggle_widget(self, widget):
        if isinstance(widget, QWidget):
            super().setCurrentWidget(widget)
            return
        result = self.find(widget)
        if result:
            super().setCurrentWidget(result)
            return
        print(f"can't toggle to widget {widget}")

    def setCurrentIndex(self, index):
        super().setCurrentIndex(index)
        if (
            len(self.opened_widget) == 0
            or not self.opened_widget[-1] is self.currentWidget()
        ):
            self.opened_widget.append(self.currentWidget())

    def setCurrentWidget(self, index):
        super().setCurrentWidget(index)
        if (
            len(self.opened_widget) == 0
            or not self.opened_widget[-1] is self.currentWidget()
        ):
            self.opened_widget.append(self.currentWidget())

    def _on_summon_widget(self, args):
        """處理 summon_widget 信號"""
        while len(args) < 3:
            args.append(None)
        args = tuple(args)
        typ, pos, hash_id = args
        try:
            att_list = self.find(typ).pack()
        except AttributeError:
            att_list = getattr(components, typ)
        if pos is not None:
            for att in att_list:
                if "X" in att:
                    att["X"] = pos[0]
                if "Y" in att:
                    att["Y"] = pos[1]
        if hash_id is None:
            hash_id = self.get_hash_id()
        self.addWidget(att_list, hash_id, True, True)

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

class AddWidget(QUndoCommand):
    def __init__(self,widget:QWidget,target:AttributePanal,id,switch):
        super().__init__()
        self.widget=widget
        self.target=target
        self.hash_id=id
        self.switch=switch

    def redo(self):
        super(AttributePanal,self.target).addWidget(self.widget,self.hash_id,self.switch)

    def undo(self):
        if self.switch:
            self.target.go_back()
            if self.target.currentWidget() is self.widget:
                self.target.go_back()

    def __del__(self):
        self.target.removeWidget(self.widget)
        self.widget.deleteLater()
