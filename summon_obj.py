import os
import re
import math
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
    QGraphicsProxyWidget,
    QGraphicsTextItem,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsPixmapItem,
    QLineEdit,
    QComboBox,
    QColorDialog,
    QGraphicsOpacityEffect,
    QGraphicsScene
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
    QRectF,
    QPointF,
    QRect,
    QPropertyAnimation,
    QEasingCurve,
    QObject,
)
from PyQt5.QtGui import (
    QPen,
    QPixmap,
    QIcon,
    QDrag,
    QCursor,
    QColor,
    QBrush,
    QPainter,
    QPainterPath,
    QTransform,
    QFontMetrics,
    QMouseEvent,
    QFont
)
from script_view import ScriptView
from common import FlowLayout, StackWidget, FontManager
import components
import numpy as np


# comunicate obj
class Signal(QObject):
    thisF = pyqtSignal(float)
    thisS = pyqtSignal(str)
    thisB = pyqtSignal(bool)

    def __init__(self, parent=None):
        self._emit=None
        super().__init__(parent)

    def connect(self, method):
        if method is self.connect or method is self.emit:
            raise RecursionError("connect method cannot be method of Signal.")
        self.thisF.connect(method)
        self.thisS.connect(method)
        self.thisB.connect(method)
        if self._emit is not None:
            self.emit(self._emit)

    def disconnect(self, method):
        self.thisF.disconnect(method)
        self.thisS.disconnect(method)

    def emit(self, value):
        self._emit=value
        if isinstance(value, bool):
            self.thisB.emit(value)
        elif isinstance(value, float) or isinstance(value, int):
            self.thisF.emit(float(value))
        else:
            try:
                self.thisS.emit(value)
            except:
                pass


# =============================================================================
# Base Layer Class
# =============================================================================
class Attribute(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.typ = dict(self.items())
        self.signal = {}
        self._emitting = set()  # 防止遞歸的標誌
        for key in self.keys():
            self.signal[key] = Signal()
            # 使用 lambda 並通過預設參數捕獲 key 值，避免閉包問題
            self.signal[key].connect(lambda value, k=key: self._on_signal(k, value))

    def __getitem__(self, key):
        """取值時自動根據類型定義轉換，避免類型錯誤"""
        value = super().__getitem__(key)
        type_def = self.typ.get(key)

        # tuple 類型: (min, max, is_int) - 數值類型
        if isinstance(type_def, tuple) and len(type_def) >= 3:
            try:
                if type_def[2] == 0:  # float
                    return float(value) if value != '' else 0.0
                else:  # int
                    return int(float(value)) if value != '' else 0
            except (ValueError, TypeError):
                return 0.0 if type_def[2] == 0 else 0

        # list 類型: 選項列表 - 返回字符串
        if isinstance(type_def, list):
            return str(value) if value else (type_def[0] if type_def else '')

        # 其他類型直接返回
        return value

    def _on_signal(self, key, value):
        """從外部信號接收值時調用，不再發射信號避免遞歸"""
        if key in self._emitting:
            return
        if key in self and self[key] == value:
            return
        super().__setitem__(key, value)

    def set_default(self, default_value: dict):
        """設置預設值，不觸發信號"""
        for key, value in default_value.items():
            if key in self:
                super().__setitem__(key, value)

    def __setitem__(self, key, value):
        """設置值並發射信號給 Layer"""
        if key in self._emitting:
            return
        if key in self and self[key] == value:
            return

        self._emitting.add(key)
        try:
            super().__setitem__(key, value)
            # 根據類型轉換值，只發射一次信號
            if isinstance(self.typ.get(key), tuple):
                emit_value = float(value) if self.typ[key][2] == 0 else int(value)
            else:
                emit_value = value
            self.signal[key].emit(emit_value)
        finally:
            self._emitting.discard(key)


class Handle(QGraphicsRectItem):
    def __init__(self, handle_type, parent=None):
        super().__init__(-4, -4, 8, 8, parent)
        self.handle_type = handle_type
        self.setBrush(QColor("#FFFFFF"))
        self.setPen(QPen(QColor("#0078D7"), 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setCursor(self._get_cursor())
        self.dragging = False
        self.start_pos = None

    def _get_cursor(self):
        cursors = {
            "top-left": Qt.SizeFDiagCursor,
            "top-right": Qt.SizeBDiagCursor,
            "bottom-left": Qt.SizeBDiagCursor,
            "bottom-right": Qt.SizeFDiagCursor,
            "top": Qt.SizeVerCursor,
            "bottom": Qt.SizeVerCursor,
            "left": Qt.SizeHorCursor,
            "right": Qt.SizeHorCursor,
        }
        return cursors.get(self.handle_type, Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.start_pos = event.scenePos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.parentItem():
            self.parentItem().resize_from_handle(
                self.handle_type, event.scenePos(), self.start_pos
            )
            self.start_pos = event.scenePos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

class RotateHandle(QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__(-5, -5, 10, 10, parent)
        self.setBrush(QColor("#4CAF50"))
        self.setPen(QPen(QColor("#2E7D32"), 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setCursor(Qt.PointingHandCursor)
        self.dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.parentItem():
            self.parentItem().rotate_from_handle(event.scenePos())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

class ComponentFrameLine(QGraphicsRectItem):
    def __init__(self, parent_item):
        # 繼承父物件的 boundingRect，並將自己設為父物件的子項
        super().__init__(parent_item.boundingRect(), parent_item)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self.handle_size = 10  # 縮放點大小
        self.rot_offset = 40  # 旋轉鈕上方偏移量
        self.handle_color = QColor("#2980b9")

        # 設定畫筆為虛線
        self.setPen(QPen(self.handle_color, 1, Qt.DashLine))

    def _get_handle_rects(self):
        """計算 9 個點的局部座標位置"""
        r = self.rect()
        s = self.handle_size
        hs = s / 2

        res = {
            "tl": QRectF(r.left() - hs, r.top() - hs, s, s),
            "tm": QRectF(r.center().x() - hs, r.top() - hs, s, s),
            "tr": QRectF(r.right() - hs, r.top() - hs, s, s),
            "mr": QRectF(r.right() - hs, r.center().y() - hs, s, s),
            "br": QRectF(r.right() - hs, r.bottom() - hs, s, s),
            "bm": QRectF(r.center().x() - hs, r.bottom() - hs, s, s),
            "bl": QRectF(r.left() - hs, r.bottom() - hs, s, s),
            "ml": QRectF(r.left() - hs, r.center().y() - hs, s, s),
        }

        # 旋轉鈕
        rot_center = QPointF(r.center().x(), r.top() - self.rot_offset)
        res["rot"] = QRectF(
            rot_center.x() - hs - 2, rot_center.y() - hs - 2, s + 4, s + 4
        )
        return res

    def boundingRect(self):
        # 必須包含所有控制點，否則繪圖會被切掉
        return self.rect().adjusted(
            -self.handle_size,
            -self.rot_offset - self.handle_size,
            self.handle_size,
            self.handle_size,
        )

    def shape(self):
        path = QPainterPath()
        res = self._get_handle_rects()
        path.addEllipse(res.pop("rot"))
        for handle in res.values():
            path.addRect(handle)
        return path

    def hoverMoveEvent(self, event):
        """當滑鼠在控制框上移動時，根據位置改變游標"""
        res = self._get_handle_rects()
        pos = event.pos()
        cursor = [
            Qt.SizeFDiagCursor,
            Qt.SizeVerCursor,
            Qt.SizeBDiagCursor,
            Qt.SizeHorCursor,
        ]
        angle = self.parentItem().rotation() % 360
        offset = int((angle + 22.5) // 45)

        # 判斷滑鼠落在哪個點上
        if res["tl"].contains(pos) or res["br"].contains(pos):
            self.setCursor(cursor[offset % 4])
        elif res["tm"].contains(pos) or res["bm"].contains(pos):
            self.setCursor(cursor[(1 + offset) % 4])
        elif res["tr"].contains(pos) or res["bl"].contains(pos):
            self.setCursor(cursor[(2 + offset) % 4])
        elif res["ml"].contains(pos) or res["mr"].contains(pos):
            self.setCursor(cursor[(3 + offset) % 4])
        elif res["rot"].contains(pos):
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        """離開控制框時恢復預設游標"""
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        res = self._get_handle_rects()
        pos = event.pos()
        if res["tl"].contains(pos) or res["br"].contains(pos):
            print("1")
        elif res["tm"].contains(pos) or res["bm"].contains(pos):
            print("2")
        elif res["tr"].contains(pos) or res["bl"].contains(pos):
            print("3")
        elif res["ml"].contains(pos) or res["mr"].contains(pos):
            print("4")
        elif res["rot"].contains(pos):
            print("5")
        else:
            pass

    def paint(self, painter, option, widget=None):
        # 設定抗鋸齒讓圓形與斜線更美觀
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 畫主虛線框
        painter.setPen(self.pen())
        painter.drawRect(self.rect())

        # 2. 畫連接旋轉鈕的直線
        handles = self._get_handle_rects()
        rot_rect = handles["rot"]
        painter.setPen(QPen(self.handle_color, 1))
        painter.drawLine(
            QPointF(self.rect().center().x(), self.rect().top()),
            QPointF(rot_rect.center().x(), rot_rect.bottom()),
        )

        # 3. 畫所有控制點
        painter.setBrush(QBrush(Qt.white))
        for name, rect in handles.items():
            if name == "rot":
                painter.setBrush(QBrush(QColor("#ecf0f1")))
                painter.drawEllipse(rect)  # 旋轉鈕畫圓的
                # 畫個簡單的小箭頭符號
                painter.drawArc(rect.adjusted(2, 2, -2, -2), 0, 270 * 16)
            else:
                painter.setBrush(QBrush(Qt.white))
                painter.drawRect(rect)  # 縮放點畫方的

class LuaText(str):
    def __init__(self,text):
        super().__init__()
# ============================================================================
# Base Component Class
# ============================================================================
class Component:
    def init_component(self, attribute: dict, id, parent:QGraphicsScene=None):
        if parent is not None:
            parent.addItem(self)
        self._parent=parent
        self.start_drag_pos = None
        self.attribute = attribute
        self.start_drag_pos = None
        self.draging = False
        self.id=id
        self.z_order=0
        self.name = ""
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.controller = ComponentFrameLine(self)
        self.controller.setVisible(False)
        self.rotate_value=0
        self.skew_x_value=0
        self.skew_y_value=0
        self.connect("X", self.move_x)
        self.connect("Y", self.move_y)
        self.connect("Skew X", self.skew_x)
        self.connect("Skew Y", self.skew_y)
        self.connect("Rotation", self.rotate)
        self.connect("Opacity", self.setLayerOpacity)
        self.connect("Display", self.display)

    def lua_translator(self):
        pass

    def rename(self, value):
        self.name = value

    def move_x(self, value):
        self.setPos(float(value), self.y())

    def move_y(self, value):
        self.setPos(self.x(), float(value))

    def gyro(self, value):
        return
    
    def skew_x(self,value):
        self.skew_x_value=value
        self.setLayerTransform()

    def skew_y(self,value):
        self.skew_y_value=value
        self.setLayerTransform()

    def shear(self, matrix, sx, sy):
        center = self.boundingRect().center()
        matrix.translate(center.x(), center.y())
        matrix.shear(-sx, -sy)
        matrix.translate(-center.x(), -center.y())
        return matrix

    def rotate(self, value):
        self.rotate_value=value
        self.setLayerTransform()

    def setLayerTransform(self, matrix=None, combine=False):
        if matrix is None: matrix=QTransform()
        print(type(self.skew_x_value),self.skew_x_value,"this")
        matrix = self.shear(
            matrix,
            np.tan(np.deg2rad(self.skew_x_value)),
            np.tan(np.deg2rad(self.skew_y_value)),
        )
        matrix.rotate(float(self.rotate_value))
        QGraphicsItem.setTransform(self, matrix, combine)

    def setLayerOpacity(self, opacity):
        opacity = float(opacity) / 100
        QGraphicsItem.setOpacity(self, opacity)

    def display(self, value):
        if value == "Always":
            pass
        if value == "Bright only":
            pass
        if value == "Dimmed only":
            pass
        if value == "Never":
            pass

    def connect(self, key, method):
        self.attribute[key].connect(method)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.controller.setVisible(bool(value) or self.controller.isSelected())
        return QGraphicsItem.itemChange(self, change, value)


class textLayer(QGraphicsTextItem, Component):
    # text
    # animation
    # font
    # text_size
    # color
    # color_dim
    # anim_scale_x
    # anim_scale_y
    # alignment
    # transform
    # shader
    # tap_action
    # text_effect
    def __init__(self, attribute: dict, id, parent=None):
        self.x_offset=0.5
        self.y_offset=0.5
        QGraphicsTextItem.__init__(self)
        Component.init_component(self, attribute, id,parent)
        self.setLayerTransform()
        self.connect("Text", self.setPlainText)
        self.connect("Font", self.setFontStyle)
        self.connect("Text size", self.setTextSize)
        self.connect("Color", self.setColor)
        self.connect("Alignment",self.setAlignment)
        # color_dim
        # animation
        # anim_scale_x
        # anim_scale_y
        # transform
        # shader
        # tap_action
        # text_effect

    def setLayerTransform(self, value=None, matrix=None, combine=False):
        if matrix is None: matrix=QTransform()
        matrix=self.shear(
            matrix,
            np.tan(np.deg2rad(self.skew_x_value)),
            np.tan(np.deg2rad(self.skew_y_value)))
        matrix2=QTransform()
        matrix2.rotate(self.rotate_value)
        matrix2=self.layerAlignment(matrix2)
        matrix3=matrix*matrix2
        QGraphicsItem.setTransform(self,matrix3)

    def layerAlignment(self,matrix):
        rect = self.boundingRect()
        align_dx = -rect.width() * self.x_offset
        align_dy = -rect.height() * self.y_offset
        matrix.translate(align_dx, align_dy)
        return matrix

    def setPlainText(self,value):
        QGraphicsTextItem.setPlainText(self,value)
        self.setLayerTransform()

    def setFontStyle(self, value):
        font_manager = FontManager()
        current_size = self.font().pointSize()
        if current_size <= 0:
            current_size = 12  # 預設大小
        font = font_manager.get_font(value, current_size)
        self.setFont(font)
        self.setLayerTransform()

    def setTextSize(self, value):
        current_font = self.font()
        size = int(value) if value else 12
        if size <= 0:
            size = 12
        current_font.setPointSize(size)
        self.setFont(current_font)
        self.setLayerTransform()

    def setColor(self, value):
        if not value:
            value = "ffffff"
        # 確保顏色值格式正確
        color_str = value if value.startswith("#") else f"#{value}"
        self.setDefaultTextColor(QColor(color_str))

    def setAlignment(self,value):
        if "c" in value.lower():
            self.x_offset=0.5
            self.y_offset=0.5
        if "l" in value:
            self.x_offset=0
        elif "i" in value:
            self.x_offset=1
        if "B" in value:
            self.y_offset=1
        elif "p" in value:
            self.y_offset=0
        self.setLayerTransform()


# ============================================================================
# Image Layer (圖片圖層)
# ============================================================================
class imageLayer(QGraphicsPixmapItem, Component):
    def __init__(self, attribute: dict, parent=None):
        self.x_offset=0.5
        self.y_offset=0.5
        QGraphicsPixmapItem.__init__(self, parent)
        Component.init_component(self, attribute)
        self.setPixmap(self.attribute["Custom image"])
        self.connect("Custom image",self.setPixmap)
        self.connect("Width",self.setLayerTransform)
        self.connect("Height",self.setLayerTransform)
        # TODO: Load actual image from Custom image path

    def setPixmap(self, pixmap):
        pixmap=QPixmap(pixmap)
        super().setPixmap(pixmap)
        self.setLayerTransform()

    def setLayerTransform(self, value=None, matrix=None, combine=False):
        if matrix is None: matrix=QTransform()
        matrix=self.shear(
            matrix,
            np.tan(np.deg2rad(self.attribute["Skew X"])),
            np.tan(np.deg2rad(self.attribute["Skew Y"])),)
        matrix2=QTransform()
        try:
            pixmap=self.pixmap()
            sw=self.attribute["Width"]/pixmap.width()
            sh=self.attribute["Height"]/pixmap.height()
            matrix2.scale(sw,sh)
        except:
            pass
        self.rotate(matrix2)
        matrix2=self.layerAlignment(matrix2)
        matrix3=matrix*matrix2
        QGraphicsItem.setTransform(self,matrix3)

    def layerAlignment(self,matrix):
        rect = self.boundingRect()
        align_dx = -rect.width() * self.x_offset
        align_dy = -rect.height() * self.y_offset
        matrix.translate(align_dx, align_dy)
        return matrix

    def setAlignment(self,value):
        if "c" in value.lower():
            self.x_offset=0.5
            self.y_offset=0.5
        if "l" in value:
            self.x_offset=0
        elif "i" in value:
            self.x_offset=1
        if "B" in value:
            self.y_offset=1
        elif "p" in value:
            self.y_offset=0
        self.setLayerTransform()

# ============================================================================
# Curved Text Layer (曲線文字圖層)
# ============================================================================
class curvedTextLayer(QGraphicsTextItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsTextItem.__init__(self, parent)
        Component.__init__(self, attribute)
        self.setPlainText(attribute.get("Text", ""))
        # TODO: Implement curved text rendering with radius


# ============================================================================
# Shape Layer (形狀圖層)
# ============================================================================
class shapeLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 100)
        height = attribute.get("Height", 100)
        self.setRect(-width / 2, -height / 2, width, height)
        color = attribute.get("Color", "#ffffff")
        if not color.startswith("#"):
            color = f"#{color}"
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(Qt.NoPen))


# ============================================================================
# Marker Layer (標記圖層)
# ============================================================================
class markerLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        radius = attribute.get("Radius", 256)
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
        self.setBrush(Qt.NoBrush)
        # TODO: Draw markers around the circle


# ============================================================================
# Tachymeter Layer (測速計圖層)
# ============================================================================
class tachymeterLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        radius = attribute.get("Radius", 230)
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
        self.setBrush(Qt.NoBrush)
        # TODO: Draw tachymeter scale


# ============================================================================
# Map Layer (地圖圖層)
# ============================================================================
class mapLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 512)
        height = attribute.get("Height", 512)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setBrush(QBrush(QColor("#3a3a3a")))
        self.setPen(QPen(QColor("#555555"), 1))
        # TODO: Load map tile from lat/lon


# ============================================================================
# Slideshow Layer (幻燈片圖層)
# ============================================================================
class slideshowLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 300)
        height = attribute.get("Height", 300)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setBrush(QBrush(QColor("#444444")))
        self.setPen(QPen(QColor("#666666"), 1))
        # TODO: Implement slideshow functionality


# ============================================================================
# Text Ring Layer (環形文字圖層)
# ============================================================================
class textRingLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        radius = attribute.get("Radius", 200)
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
        self.setBrush(Qt.NoBrush)
        # TODO: Draw numbers around the ring


# ============================================================================
# Rounded Rectangle Layer (圓角矩形圖層)
# ============================================================================
class roundedRectangleLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 300)
        height = attribute.get("Height", 200)
        self.setRect(-width / 2, -height / 2, width, height)
        color = attribute.get("Color", "#ffffff")
        if not color.startswith("#"):
            color = f"#{color}"
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(Qt.NoPen))
        # TODO: Apply corner radius


# ============================================================================
# Series Layer (數據系列圖層)
# ============================================================================
class seriesLayer(QGraphicsTextItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsTextItem.__init__(self, parent)
        Component.__init__(self, attribute)
        self.setPlainText("MON\nTUE\nWED")
        # TODO: Implement series data display


# ============================================================================
# Complication Layer (複雜功能圖層)
# ============================================================================
class complicationLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 100)
        height = attribute.get("Height", 100)
        self.setRect(-width / 2, -height / 2, width, height)
        bg_color = attribute.get("Color background", "#494949")
        if not bg_color.startswith("#"):
            bg_color = f"#{bg_color}"
        self.setBrush(QBrush(QColor(bg_color)))
        self.setPen(QPen(QColor("#666666"), 1))


# ============================================================================
# Chart Layer (圖表圖層)
# ============================================================================
class chartLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 205)
        height = attribute.get("Height", 76)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setBrush(QBrush(QColor("#2a2a2a")))
        self.setPen(QPen(QColor("#444444"), 1))
        # TODO: Draw chart


# ============================================================================
# Image Condition Layer (條件圖片圖層)
# ============================================================================
class imageCondLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 80)
        height = attribute.get("Height", 80)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setBrush(QBrush(QColor("#555555")))
        self.setPen(QPen(QColor("#777777"), 1))
        # TODO: Implement conditional image selection


# ============================================================================
# Image GIF Layer (GIF圖片圖層)
# ============================================================================
class imageGifLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 100)
        height = attribute.get("Height", 100)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setBrush(QBrush(QColor("#4a4a4a")))
        self.setPen(QPen(QColor("#666666"), 1))
        # TODO: Load and animate GIF


# ============================================================================
# Progress Layer (進度條圖層)
# ============================================================================
class progressLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        QGraphicsRectItem.__init__(self, parent)
        Component.__init__(self, attribute)
        width = attribute.get("Width", 114)
        height = attribute.get("Height", 24)
        self.setRect(-width / 2, -height / 2, width, height)
        bg_color = attribute.get("Color 3", "#525151")
        if not bg_color.startswith("#"):
            bg_color = f"#{bg_color}"
        self.setBrush(QBrush(QColor(bg_color)))
        self.setPen(QPen(Qt.NoPen))
        # TODO: Draw progress indicator


# ============================================================================
# Ring Layer (圓環圖層)
# ============================================================================
class ringLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        super().__init__(parent)
        Component.__init__(self, attribute)
        radius = attribute.get("Radius outer", 57)
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        color = attribute.get("Color", "#ffffff")
        if not color.startswith("#"):
            color = f"#{color}"
        self.setPen(QPen(QColor(color), 4))
        self.setBrush(Qt.NoBrush)
        # TODO: Draw ring arc


# ============================================================================
# Markers HM Layer (時分標記圖層)
# ============================================================================
class markersHMLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        super().__init__(parent)
        Component.__init__(self, attribute)
        radius = attribute.get("Radius", 256)
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
        self.setBrush(Qt.NoBrush)
        # TODO: Draw hour/minute markers


# ============================================================================
# Directional Light Layer (方向光源圖層)
# ============================================================================
class directionalLightLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        super().__init__(parent)
        Component.__init__(self, attribute)
        self.setRect(-30, -30, 60, 60)
        color = attribute.get("Color", "#ffffff")
        if not color.startswith("#"):
            color = f"#{color}"
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#ffff00"), 2))
        # Light indicator


# ============================================================================
# 3D Layer (3D圖層)
# ============================================================================
class layer3D(QGraphicsRectItem, Component):
    def __init__(self, attribute: Attribute, parent=None):
        super().__init__(parent)
        Component.__init__(self, attribute)
        scale_x = attribute.get("Scale X", 40)
        scale_y = attribute.get("Scale Y", 40)
        self.setRect(-scale_x / 2, -scale_y / 2, scale_x, scale_y)
        self.setBrush(QBrush(QColor("#666666")))
        self.setPen(QPen(QColor("#888888"), 2))
        # TODO: Implement 3D rendering


# ============================================================================
# Layer Type Mapping (圖層類型映射)
# ============================================================================
LAYER_CLASS_MAP = {
    "textLayer": textLayer,
    "imageLayer": imageLayer,
    "curvedTextLayer": curvedTextLayer,
    "shapeLayer": shapeLayer,
    "markerLayer": markerLayer,
    "tachymeterLayer": tachymeterLayer,
    "mapLayer": mapLayer,
    "slideshowLayer": slideshowLayer,
    "textRingLayer": textRingLayer,
    "roundedRectangleLayer": roundedRectangleLayer,
    "seriesLayer": seriesLayer,
    "complicationLayer": complicationLayer,
    "chartLayer": chartLayer,
    "imageCondLayer": imageCondLayer,
    "imageGifLayer": imageGifLayer,
    "progressLayer": progressLayer,
    "ringLayer": ringLayer,
    "markersHMLayer": markersHMLayer,
    "directionalLightLayer": directionalLightLayer,
    "layer3D": layer3D,
    "3DLayer": layer3D,
}


def create_layer(layer_type: str, signal_dict: dict,id:int, parent=None):
    """根據圖層類型創建對應的圖層實例"""
    layer_class = LAYER_CLASS_MAP.get(layer_type, textLayer)
    return layer_class(signal_dict,id, parent)
