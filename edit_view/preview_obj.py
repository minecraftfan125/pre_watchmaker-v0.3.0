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
    QGraphicsEllipseItem,
    QGraphicsView,
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

class BatchProcessContainer:
    def __init__(self, container):
        iter(container)
        self._container = container

    def __getitem__(self, key):
        return self._container[key]

    def __len__(self):
        return len(self._container)

    def __iter__(self):
        return iter(self._container)

    def __contains__(self, item):
        return item in self._container
    
    def __setitem__(self, key, value):
        self._container[key] = value

    def __delitem__(self, key):
        del self._container[key]

    def __repr__(self):
        return f"{self.__class__.__name__}({self._container!r})"

    def __getattr__(self, name):
        if hasattr(self._container, name):
            return getattr(self._container, name)
        
        is_callable_feature = None 
        
        if isinstance(self._container, dict):
            result_dict = {}
            for key, value in self._container.items():
                var = getattr(value, name)
                
                current_is_callable = callable(var)
                if is_callable_feature is None:
                    is_callable_feature = current_is_callable
                elif is_callable_feature != current_is_callable:
                    raise AttributeError(f"All elements of {type(self)} should have the same feature type for '{name}'")
                
                result_dict[key] = var

            return BatchProcessContainer(result_dict)

        result_list = []
        for item in self._container:
            var = getattr(item, name)
            
            current_is_callable = callable(var)
            if is_callable_feature is None:
                is_callable_feature = current_is_callable
            elif is_callable_feature != current_is_callable:
                raise AttributeError(f"All elements of {type(self)} should have the same feature type for '{name}'")
            
            result_list.append(var)
            
        return BatchProcessContainer(result_list)
            
    def __call__(self, *args, **kwargs):
        if isinstance(self._container, dict):
            result_dict = {}
            for key, func in self._container.items():
                if not callable(func):
                    raise TypeError(f"Item at key '{key}' is not callable")
                result_dict[key] = func(*args, **kwargs)
            return BatchProcessContainer(result_dict)
        
        result_list = []
        for func in self._container:
            if not callable(func):
                raise TypeError(f"Item {func!r} inside container is not callable")
            result_list.append(func(*args, **kwargs))
        return BatchProcessContainer(result_list)

# =============================================================================
# Base Layer Class
# =============================================================================
class RotateHandle(QGraphicsEllipseItem):
    def __init__(self,parent):
        super().__init__(-6, -6, 12, 12,parent)
        self.parent=parent
        self.setFlags(
            QGraphicsItem.ItemIgnoresTransformations
            )
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(80, 150, 220),1.5))

    def update_pos(self):
        t = self.parent.sceneTransform()
        # 利用矩陣向量 (m21, m22) 計算 Y 軸的真實視覺縮放比例
        sy = math.hypot(t.m21(), t.m22())
        if sy == 0: sy = 1.0 # 避免除以零
        
        # 假設我們希望視覺上永遠距離頂端 40 像素
        visual_distance = 40 
        
        # 將視覺距離除以 sy，得到抵消縮放後的局部 Y 座標
        rect = self.parent.boundingRect()
        self.setPos(rect.width() // 2, -visual_distance / sy)

    def itemChange(self, change, value):

        if change== QGraphicsItem.ItemVisibleHasChanged and value:
            self.update_pos()
        return super().itemChange(change, value)
    
        
class ScaleHandle(QGraphicsRectItem):
    _direction={
        "tl":(0 , 0),
        "tc":(0.5 , 0),
        "tr":(1 , 0),
        "cl":(0 , 0.5),
        "cr":(1 , 0.5),
        "bl":(0 , 1),
        "bc":(0.5 , 1),
        "br":(1 , 1)
        }
    def __init__(self,direction,parent):
        super().__init__(QRectF(-5,-5,10,10),parent)
        self.setFlags(
            QGraphicsItem.ItemIgnoresTransformations
            )
        self.setBrush(QBrush(QColor(100, 180, 255)))
        self.setPen(QPen(Qt.white, 1))
        self.direction=direction
        parent.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def update_transform(self):
        #手動抵消父元件的縮放
        p = self.parentItem()
        if not p: return

        # 取得父元件在場景中的總縮放比例
        # 我們利用 transform 矩陣來提取縮放數值
        t = p.sceneTransform()
        sx = t.m11() # X 軸縮放
        sy = t.m22() # Y 軸縮放
        
        # 套用反向縮放，但保持位移與旋轉由父元件主導
        inverse_t = QTransform()
        inverse_t.scale(1.0/sx if sx != 0 else 1, 1.0/sy if sy != 0 else 1)
        self.setTransform(inverse_t,True)

    def update_pos(self,w,h):
        x=self._direction[self.direction][0]*w
        y=self._direction[self.direction][1]*h
        self.setPos(x,y)

    @classmethod
    def create_Handle(cls,parent):
        handles={}
        w,h=parent.boundingRect().width(),parent.boundingRect().height()
        for direction in cls._direction:
            handle=cls(direction,parent)
            x=cls._direction[direction][0]*w
            y=cls._direction[direction][1]*h
            handle.setPos(x,y)
            handles[direction]=handle
        return BatchProcessContainer(handles)

class SelectionBox(QGraphicsRectItem):
    def __init__(self,parent):
        super().__init__(QRectF(0,0,0,0),parent)
        self.parent: Component|QGraphicsItem = parent
        self.parent_rect=QRectF(0,0,0,0)
        self.setFlags(
            QGraphicsItem.ItemIgnoresParentOpacity
            )
        
        dashed_pen = QPen(QColor(80, 150, 220),1)
        dashed_pen.setStyle(Qt.DashLine)
        dashed_pen.setCosmetic(True)
        self.setPen(dashed_pen)
        self.setBrush(QBrush(Qt.transparent))

        rotate_method=getattr(self.parent,"set_rotate",False)
        bounding_rect=self.boundingRect()
        if rotate_method:
            self.rotate=RotateHandle(self)
            self.rotate.setPos(bounding_rect.width()//2,-50)
            self.rotate.setZValue(0)

        scale_method=getattr(self.parent,"set_scale",False)
        if scale_method:
            self.scale_handle=ScaleHandle.create_Handle(self)
            self.scale_handle.setZValue(1)
        self.update_scale()

    # ▼ 新增這個方法：動態計算控制點位置，抵消父元件縮放
    def update_scale(self):
        parent_rotate=self.parent.rotation()
        self.parent.setRotation(0)
        rect=self.parent.sceneBoundingRect()
        print(self.parent.sceneBoundingRect())
        rect.moveTo(0,0)
        self.setRect(rect)
        self.scale_handle.update_pos(self.rect().width(),self.rect().height())
        self.rotate.update_pos()
        self.parent_rect=rect
        self.parent.setRotation(parent_rotate)

    def itemChange(self, change, value):
        if (change == QGraphicsItem.ItemScaleHasChanged):
            self.scale_handle.update_transform()
            self.rotate.update_pos()
        if (change == QGraphicsItem.ItemVisibleChange):
            print("show",self.rect())
        return super().itemChange(change, value)


class GraphicsScene(QGraphicsScene):
    def __init__(self):
        super().__init__()

    def addItem(self, item):
        super().addItem(item)

# ============================================================================
# Base Component Class
# ============================================================================
class Component:
    def init_component(self, attribute: dict, id, parent:QGraphicsScene=None):
        self._parent=parent
        self.start_drag_pos = None
        self.attribute = attribute
        self.start_drag_pos = None
        self.draging = False
        self.id=id
        self.z_order=0
        self.name = ""
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.rotate_value=0
        self.skew_x_value=0
        self.skew_y_value=0
        self.controller = SelectionBox(self)
        self.controller.setVisible(False)
        self.connect("Layer", self.order)
        self.connect("X", self.move_x)
        self.connect("Y", self.move_y)
        self.connect("Skew X", self.skew_x)
        self.connect("Skew Y", self.skew_y)
        self.connect("Rotation", self.rotate)
        self.connect("Opacity", self.setLayerOpacity)
        self.connect("Display", self.display)

    def lua_translator(self):
        pass

    def order(self,value):
        self.setZValue(-999+value)

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
        matrix = self.shear(
            matrix,
            np.tan(np.deg2rad(self.skew_x_value)),
            np.tan(np.deg2rad(self.skew_y_value)),
        )
        matrix.rotate(float(self.rotate_value))
        QGraphicsItem.setTransform(self, matrix, combine)
        self.controller.update_scale()

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
        if key in self.attribute:
            self.attribute[key].connect(method)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            print(self,"select")
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
        self.controller.update_scale()

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

    def set_rotate(self):
        pass
    def set_scale(self):
        pass


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
        self.controller.update_scale()

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
    def __init__(self, attribute: dict, parent=None):
        QGraphicsTextItem.__init__(self, parent)
        Component.__init__(self, attribute)
        self.setPlainText(attribute.get("Text", ""))
        # TODO: Implement curved text rendering with radius


# ============================================================================
# Shape Layer (形狀圖層)
# ============================================================================
class shapeLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
        QGraphicsTextItem.__init__(self, parent)
        Component.__init__(self, attribute)
        self.setPlainText("MON\nTUE\nWED")
        # TODO: Implement series data display


# ============================================================================
# Complication Layer (複雜功能圖層)
# ============================================================================
class complicationLayer(QGraphicsRectItem, Component):
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
    def __init__(self, attribute: dict, parent=None):
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
