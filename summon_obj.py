import os
import math
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QSplitter, QScrollArea, QSizePolicy, QPushButton,
                             QGridLayout, QTreeWidget, QTreeWidgetItem,
                             QStackedWidget, QListWidget, QListWidgetItem,
                             QLineEdit, QComboBox, QColorDialog, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QPoint, QMimeData, pyqtSignal, QSize, QThread, QTimer, QEvent, QRect, QPropertyAnimation, QEasingCurve, QObject
from PyQt5.QtGui import QPixmap, QIcon, QDrag, QCursor, QColor, QPainter, QTransform, QFontMetrics
from script_view import ScriptView
from common import FlowLayout, WatchFaceText, StackWidget
import components

# ============================================================================
# Base Component Class
# ============================================================================
class Component(QWidget):
    def __init__(self, attributes=None, parent=None):
        super().__init__(parent)
        self.attributes = {}
        if attributes is not None:
            self.attributes = attributes
        self.setAttribute(Qt.WA_TranslucentBackground)

    def validity_testing(self,value,typ):
        try:
            return typ(value)
        except:
            return self.compilation(value)
        
    def compilation(self,script):
        return None

    def connect(self, key, external_signal, external_method=None):
        if key not in self.attributes:
            raise NameError(f"{key} not in attribute")
        internal_signal = getattr(self, "_" + key, False)
        internal_method = getattr(self, key, False)

        def set_value(value):
            if internal_method:
                self.attributes[key] = value
                internal_method(value)
            else:
                print(f"WARNING: implementation {key} methods may be required")

        external_signal.connect(set_value)
        if external_method is not None and internal_signal:
            internal_signal.connect(external_method)

    def get_attributes(self):
        return self.attributes

    def paintEvent(self, event):
        """
        統一處理 alignment 偏移、rotation 旋轉和 skew 變換
        - alignment: 決定繪製錨點 (tl, tc, tr, cl, cc, cr, bl, bc, br)
        - rotation: 以物件座標原點為軸旋轉 (0-360 度)
        - skew_x: y 軸順時針旋轉角度 (-90 ~ 90)，圖形變成平行四邊形
        - skew_y: x 軸順時針旋轉角度 (-90 ~ 90)
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 安全獲取屬性值（沒有這些屬性的物件使用預設值）
        align_state = getattr(self, '_align_state', 'tl')
        rotation = getattr(self, '_rotation_angle', 0)
        skew_x = getattr(self, '_skew_x_value', 0)
        skew_y = getattr(self, '_skew_y_value', 0)

        # 限制 skew 範圍並檢查是否消失
        skew_x = max(-90, min(90, skew_x))
        skew_y = max(-90, min(90, skew_y))
        if abs(skew_x) >= 90 or abs(skew_y) >= 90:
            painter.end()
            return

        w, h = self.width(), self.height()

        # 根據 alignment 計算偏移量
        # 第一個字符: 垂直對齊 (t=top, c=center, b=bottom)
        # 第二個字符: 水平對齊 (l=left, c=center, r=right)
        offset_x, offset_y = 0, 0

        if len(align_state) >= 1:
            v_align = align_state[0]
            if v_align == 'c':
                offset_y = -h / 2
            elif v_align == 'b':
                offset_y = -h
            # 't' 不需要偏移

        if len(align_state) >= 2:
            h_align = align_state[1]
            if h_align == 'c':
                offset_x = -w / 2
            elif h_align == 'r':
                offset_x = -w
            # 'l' 不需要偏移

        # 建立變換矩陣
        transform = QTransform()

        # 1. 先根據 alignment 偏移原點
        transform.translate(offset_x, offset_y)

        # 2. 應用 rotation 旋轉（以物件座標原點為軸）
        transform.rotate(rotation)

        # 3. 應用 skew 變換
        # skew_x: y 軸順時針旋轉，使用 shear 的水平分量
        # skew_y: x 軸順時針旋轉，使用 shear 的垂直分量
        # shear(sh, sv): x' = x + sh*y, y' = sv*x + y
        shear_h = math.tan(math.radians(skew_x))
        shear_v = math.tan(math.radians(skew_y))
        transform.shear(shear_h, shear_v)

        painter.setTransform(transform)

        # 呼叫子類的繪製方法
        self._drawContent(painter)

        painter.end()

    def _drawContent(self, painter):
        """
        子類重寫此方法來繪製內容
        painter 已經套用了 alignment 和 skew 變換
        """
        pass

# ============================================================================
# Common Classes Cache (延遲建立)
# ============================================================================
_common_classes = {}

def common_factory(common_type):
    """
    取得或建立 common 類別
    common_type: "position", "transform", "size", "color", "display",
                 "interaction", "shadow", "outline", "shader", "blend",
                 "anim_scale", "protected"
    """
    if common_type in _common_classes:
        return _common_classes[common_type]

    # Position - 基礎定位屬性
    if common_type == "position":
        class Position(Component):
            _x = pyqtSignal(object)
            _y = pyqtSignal(object)
            _rotation = pyqtSignal(object)
            _opacity = pyqtSignal(object)
            _alignment = pyqtSignal(object)

            def _init_position(self):
                """初始化 Position 屬性（由子類調用）"""
                self._opacity_effect = QGraphicsOpacityEffect(self)
                self._opacity_effect.setOpacity(1.0)
                self._rotation_angle = 0
                self._align_state = "tl"

            def x(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.move(value, self.y())
                    self._x.emit(value)
                return super().x()

            def y(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.move(self.x(), value)
                    self._y.emit(value)
                return super().y()

            def rotation(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._rotation_angle = value
                    self.update()
                    self._rotation.emit(value)
                return self._rotation_angle

            def opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._opacity_effect.setOpacity(value * 0.01)
                    self.setGraphicsEffect(self._opacity_effect)
                    self._opacity.emit(value)
                return self._opacity_effect.opacity()

            def alignment(self, value=None):
                """
                設定對齊方式，由 paintEvent 處理繪製偏移
                value: 兩個字符的字串
                  - 第一個字符: 垂直對齊 (t=top, c=center, b=bottom)
                  - 第二個字符: 水平對齊 (l=left, c=center, r=right)
                例如: "cc" = 中心對齊, "tl" = 左上對齊, "br" = 右下對齊
                """
                value = self.validity_testing(value, str)
                if value is None:
                    return self._align_state
                self._align_state = value
                self.update()
                self._alignment.emit(value)
                return self._align_state

        _common_classes[common_type] = Position
        return Position

    # Transform - 變換屬性
    elif common_type == "transform":
        class Transform(Component):
            _gyro = pyqtSignal(object)
            _skew_x = pyqtSignal(object)
            _skew_y = pyqtSignal(object)
            _scale_x = pyqtSignal(object)
            _scale_y = pyqtSignal(object)

            def _init_transform(self):
                """初始化 Transform 屬性（由子類調用）"""
                self._gyro_value = 0
                self._skew_x_value = 0
                self._skew_y_value = 0
                self._scale_x_value = 100
                self._scale_y_value = 100

            def gyro(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._gyro_value = value
                    self.update()
                    self._gyro.emit(value)
                return self._gyro_value

            def skew_x(self, value=None):
                """
                設定 X 軸傾斜角度 (-90 ~ 90)
                正值: y 軸順時針旋轉，圖形向右傾斜
                負值: y 軸逆時針旋轉，圖形向左傾斜
                ±90 時圖形消失
                """
                value = self.validity_testing(value, int)
                if value is not None:
                    self._skew_x_value = max(-90, min(90, value))
                    self.update()
                    self._skew_x.emit(value)
                return self._skew_x_value

            def skew_y(self, value=None):
                """
                設定 Y 軸傾斜角度 (-90 ~ 90)
                正值: x 軸順時針旋轉，圖形向下傾斜
                負值: x 軸逆時針旋轉，圖形向上傾斜
                ±90 時圖形消失
                """
                value = self.validity_testing(value, int)
                if value is not None:
                    self._skew_y_value = max(-90, min(90, value))
                    self.update()
                    self._skew_y.emit(value)
                return self._skew_y_value

            def scale_x(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._scale_x_value = value
                    self.update()
                    self._scale_x.emit(value)
                return self._scale_x_value

            def scale_y(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._scale_y_value = value
                    self.update()
                    self._scale_y.emit(value)
                return self._scale_y_value

        _common_classes[common_type] = Transform
        return Transform

    # Size - 尺寸屬性
    elif common_type == "size":
        class Size(Component):
            _width = pyqtSignal(object)
            _height = pyqtSignal(object)

            def _init_size(self):
                """初始化 Size 屬性（由子類調用）"""
                pass  # Size 使用 QWidget 內建的 width/height

            def width(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.resize(value, self.height())
                    self._width.emit(value)
                return super().width()

            def height(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.resize(self.width(), value)
                    self._height.emit(value)
                return super().height()

        _common_classes[common_type] = Size
        return Size

    # Color - 顏色屬性
    elif common_type == "color":
        class Color(Component):
            _color = pyqtSignal(object)
            _color_dim = pyqtSignal(object)

            def _init_color(self):
                """初始化 Color 屬性（由子類調用）"""
                self._color_value = "ffffff"
                self._color_dim_value = ""

            def color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._color_value = value
                    self._color.emit(value)
                return self._color_value

            def color_dim(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._color_dim_value = value
                    self._color_dim.emit(value)
                return self._color_dim_value

        _common_classes[common_type] = Color
        return Color

    # Display - 顯示屬性
    elif common_type == "display":
        class Display(Component):
            _display = pyqtSignal(object)

            def _init_display(self):
                """初始化 Display 屬性（由子類調用）"""
                self._display_value = "bd"

            def display(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._display_value = value
                    self._display.emit(value)
                return self._display_value

        _common_classes[common_type] = Display
        return Display

    # Interaction - 互動屬性
    elif common_type == "interaction":
        class Interaction(Component):
            _tap_action = pyqtSignal(object)

            def _init_interaction(self):
                """初始化 Interaction 屬性（由子類調用）"""
                self._tap_action_value = ""

            def tap_action(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._tap_action_value = value
                    self._tap_action.emit(value)
                return self._tap_action_value

        _common_classes[common_type] = Interaction
        return Interaction

    # Shadow - 陰影效果
    elif common_type == "shadow":
        class Shadow(Component):
            _shadow = pyqtSignal(object)
            _w_color = pyqtSignal(object)
            _w_distance = pyqtSignal(object)
            _w_opacity = pyqtSignal(object)

            def _init_shadow(self):
                """初始化 Shadow 屬性（由子類調用）"""
                self._shadow_value = ""
                self._w_color_value = "000000"
                self._w_distance_value = 4
                self._w_opacity_value = 100

            def shadow(self, value=None):
                # 實作複雜，先 pass
                value = self.validity_testing(value, str)
                if value is not None:
                    self._shadow_value = value
                    self._shadow.emit(value)
                return self._shadow_value

            def w_color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._w_color_value = value
                    self._w_color.emit(value)
                return self._w_color_value

            def w_distance(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._w_distance_value = value
                    self._w_distance.emit(value)
                return self._w_distance_value

            def w_opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._w_opacity_value = value
                    self._w_opacity.emit(value)
                return self._w_opacity_value

        _common_classes[common_type] = Shadow
        return Shadow

    # Outline - 描邊效果
    elif common_type == "outline":
        class Outline(Component):
            _outline = pyqtSignal(object)
            _o_color = pyqtSignal(object)
            _o_size = pyqtSignal(object)
            _o_opacity = pyqtSignal(object)

            def _init_outline(self):
                """初始化 Outline 屬性（由子類調用）"""
                self._outline_value = ""
                self._o_color_value = "000000"
                self._o_size_value = 2
                self._o_opacity_value = 100

            def outline(self, value=None):
                # 實作複雜，先 pass
                value = self.validity_testing(value, str)
                if value is not None:
                    self._outline_value = value
                    self._outline.emit(value)
                return self._outline_value

            def o_color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._o_color_value = value
                    self._o_color.emit(value)
                return self._o_color_value

            def o_size(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._o_size_value = value
                    self._o_size.emit(value)
                return self._o_size_value

            def o_opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._o_opacity_value = value
                    self._o_opacity.emit(value)
                return self._o_opacity_value

        _common_classes[common_type] = Outline
        return Outline

    # Shader - 著色器效果
    elif common_type == "shader":
        class Shader(Component):
            _shader = pyqtSignal(object)
            _u_1 = pyqtSignal(object)
            _u_2 = pyqtSignal(object)
            _u_3 = pyqtSignal(object)
            _u_4 = pyqtSignal(object)
            _u_5 = pyqtSignal(object)

            def _init_shader(self):
                """初始化 Shader 屬性（由子類調用）"""
                self._shader_value = ""
                self._u_1_value = ""
                self._u_2_value = ""
                self._u_3_value = ""
                self._u_4_value = ""
                self._u_5_value = ""

            def shader(self, value=None):
                # 實作複雜，先 pass
                value = self.validity_testing(value, str)
                if value is not None:
                    self._shader_value = value
                    self._shader.emit(value)
                return self._shader_value

            def u_1(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_1_value = value
                    self._u_1.emit(value)
                return self._u_1_value

            def u_2(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_2_value = value
                    self._u_2.emit(value)
                return self._u_2_value

            def u_3(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_3_value = value
                    self._u_3.emit(value)
                return self._u_3_value

            def u_4(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_4_value = value
                    self._u_4.emit(value)
                return self._u_4_value

            def u_5(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_5_value = value
                    self._u_5.emit(value)
                return self._u_5_value

        _common_classes[common_type] = Shader
        return Shader

    # Blend - 混合模式
    elif common_type == "blend":
        class Blend(Component):
            _blend_mode = pyqtSignal(object)

            def _init_blend(self):
                """初始化 Blend 屬性（由子類調用）"""
                self._blend_mode_value = ""

            def blend_mode(self, value=None):
                # 實作複雜，先 pass
                value = self.validity_testing(value, str)
                if value is not None:
                    self._blend_mode_value = value
                    self._blend_mode.emit(value)
                return self._blend_mode_value

        _common_classes[common_type] = Blend
        return Blend

    # AnimScale - 動畫縮放
    elif common_type == "anim_scale":
        class AnimScale(Component):
            _anim_scale_x = pyqtSignal(object)
            _anim_scale_y = pyqtSignal(object)

            def _init_anim_scale(self):
                """初始化 AnimScale 屬性（由子類調用）"""
                self._anim_scale_x_value = ""
                self._anim_scale_y_value = ""

            def anim_scale_x(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._anim_scale_x_value = value
                    self._anim_scale_x.emit(value)
                return self._anim_scale_x_value

            def anim_scale_y(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._anim_scale_y_value = value
                    self._anim_scale_y.emit(value)
                return self._anim_scale_y_value

        _common_classes[common_type] = AnimScale
        return AnimScale

    # Protected - 保護屬性
    elif common_type == "protected":
        class Protected(Component):
            _protected = pyqtSignal(object)

            def _init_protected(self):
                """初始化 Protected 屬性（由子類調用）"""
                self._protected_value = ""

            def protected(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._protected_value = value
                    self._protected.emit(value)
                return self._protected_value

        _common_classes[common_type] = Protected
        return Protected

    else:
        raise ValueError(f"Unknown common type: {common_type}")


# ============================================================================
# Component Classes Cache (延遲建立)
# ============================================================================
_component_classes = {}

# 定義各 component_type 需要繼承的 common 類別
_component_common_map = {
    "text": ["position", "transform", "color", "display", "interaction", "anim_scale", "shadow", "outline", "shader", "blend"],
    "text_animation": ["position", "transform", "color", "display", "shadow", "outline"],
    "text_curved": ["position", "color", "display", "shadow", "outline"],
    "text_ring": ["position", "display", "shadow", "outline"],
    "image": ["position", "transform", "size", "display", "interaction", "anim_scale", "shadow", "shader", "blend", "protected"],
    "image_gif": ["position", "size", "display"],
    "image_cutout": ["position", "size", "display"],
    "video": ["position", "size", "display"],
    "shape": ["position", "transform", "size", "display", "interaction", "shadow", "outline", "shader", "blend"],
    "rounded": ["position", "size", "display", "shader"],
    "ring": ["position", "display"],
    "ring_image": ["position", "display"],
    "progress": ["position", "size", "display"],
    "progress_image": ["position", "size", "display"],
    "chart": ["position", "size", "display"],
    "markers": ["position", "display", "shadow"],
    "markers_hm": ["position", "display", "anim_scale"],
    "tachy": ["position", "display"],
    "series": ["position", "display", "shadow", "outline"],
    "map": ["position", "size", "display"],
    "gallery_2d": ["position", "size", "display", "protected"],
    "model_3d": ["display"],
    "text_3d": ["display"],
    "camera": ["display"],
    "light_dir": [],
    "complication": ["position", "size", "display"],
    "group": ["position", "transform", "display"],
}


def _init_all_commons(instance, common_types):
    """
    呼叫所有 common 類別的 _init_xxx 方法
    """
    init_map = {
        "position": "_init_position",
        "transform": "_init_transform",
        "size": "_init_size",
        "color": "_init_color",
        "display": "_init_display",
        "interaction": "_init_interaction",
        "shadow": "_init_shadow",
        "outline": "_init_outline",
        "shader": "_init_shader",
        "blend": "_init_blend",
        "anim_scale": "_init_anim_scale",
        "protected": "_init_protected",
    }
    for ct in common_types:
        init_method_name = init_map.get(ct)
        if init_method_name:
            init_method = getattr(instance, init_method_name, None)
            if init_method:
                init_method()


def components_factory(component_type, attribute):
    """
    取得或建立 component 類別實例
    使用動態多重繼承，繼承對應的 common 類別
    """
    if component_type in _component_classes:
        return _component_classes[component_type](attribute)

    # 取得這個 component_type 需要的 common 類別
    common_types = _component_common_map.get(component_type, ["position"])

    # 動態建立基底類別列表
    bases = []
    for ct in common_types:
        bases.append(common_factory(ct))

    # 確保至少繼承 Component
    if not bases:
        bases = [Component]

    # 根據 component_type 建立對應的類別
    if component_type == "text":
        # Text 特殊處理：繼承 WatchFaceText
        # WatchFaceText 必須放在最前面，確保 super().__init__ 正確呼叫 QLabel
        # 不使用動態繼承 bases，因為會破壞 WatchFaceText 的 MRO
        class Text(WatchFaceText):
            _text = pyqtSignal(object)
            _text_size = pyqtSignal(object)
            _font = pyqtSignal(object)
            _transform = pyqtSignal(object)
            _name = pyqtSignal(object)
            # 從 common classes 複製信號定義
            _x = pyqtSignal(object)
            _y = pyqtSignal(object)
            _rotation = pyqtSignal(object)
            _opacity = pyqtSignal(object)
            _alignment = pyqtSignal(object)
            _gyro = pyqtSignal(object)
            _skew_x = pyqtSignal(object)
            _skew_y = pyqtSignal(object)
            _scale_x = pyqtSignal(object)
            _scale_y = pyqtSignal(object)
            _color = pyqtSignal(object)
            _color_dim = pyqtSignal(object)
            _display = pyqtSignal(object)
            _tap_action = pyqtSignal(object)
            _anim_scale_x = pyqtSignal(object)
            _anim_scale_y = pyqtSignal(object)
            _shadow = pyqtSignal(object)
            _w_color = pyqtSignal(object)
            _w_distance = pyqtSignal(object)
            _w_opacity = pyqtSignal(object)
            _outline = pyqtSignal(object)
            _o_color = pyqtSignal(object)
            _o_size = pyqtSignal(object)
            _o_opacity = pyqtSignal(object)
            _shader = pyqtSignal(object)
            _u_1 = pyqtSignal(object)
            _u_2 = pyqtSignal(object)
            _u_3 = pyqtSignal(object)
            _u_4 = pyqtSignal(object)
            _u_5 = pyqtSignal(object)
            _blend_mode = pyqtSignal(object)

            def __init__(self, attributes=None, parent=None):
                text_content = attributes.get("text", "") if attributes else ""
                super().__init__(text_content, parent)

                # 初始化 Component 屬性
                self.attributes = attributes if attributes else {}
                self.setAttribute(Qt.WA_TranslucentBackground)

                # 手動初始化所有 common 屬性
                # Position
                self._opacity_effect = QGraphicsOpacityEffect(self)
                self._opacity_effect.setOpacity(1.0)
                self._rotation_angle = 0
                self._align_state = "tl"
                # Transform
                self._gyro_value = 0
                self._skew_x_value = 0
                self._skew_y_value = 0
                self._scale_x_value = 100
                self._scale_y_value = 100
                # Color
                self._color_value = "ffffff"
                self._color_dim_value = ""
                # Display
                self._display_value = "bd"
                # Interaction
                self._tap_action_value = ""
                # AnimScale
                self._anim_scale_x_value = ""
                self._anim_scale_y_value = ""
                # Shadow
                self._shadow_value = ""
                self._w_color_value = "000000"
                self._w_distance_value = 4
                self._w_opacity_value = 100
                # Outline
                self._outline_value = ""
                self._o_color_value = "000000"
                self._o_size_value = 2
                self._o_opacity_value = 100
                # Shader
                self._shader_value = ""
                self._u_1_value = ""
                self._u_2_value = ""
                self._u_3_value = ""
                self._u_4_value = ""
                self._u_5_value = ""
                # Blend
                self._blend_mode_value = ""

                # Text 專屬屬性
                self._text_value = text_content
                self._text_size_value = 40
                self._font_value = "Roboto-Regular"
                self._transform_value = "n"
                self._name_value = "Text Layer"

                # 初始調整大小
                self._adjustSize()

            def _adjustSize(self):
                """根據文字內容、字型和 alignment 自動調整 Label 大小"""
                font = QLabel.font(self)
                fm = QFontMetrics(font)
                text = self._text_value if hasattr(self, '_text_value') else ''
                # 計算文字所需的寬度和高度，加上一些 padding
                text_width = fm.horizontalAdvance(text) + 10
                text_height = fm.height() + 6

                # 儲存文字實際大小供 paintEvent 使用
                self._text_render_width = text_width
                self._text_render_height = text_height

                # 根據 alignment 計算 Label 需要的大小
                # alignment 偏移是根據文字大小計算，Label 要能容納偏移後的文字
                align_state = getattr(self, '_align_state', 'tl')

                final_width = text_width
                final_height = text_height

                if len(align_state) >= 1:
                    v_align = align_state[0]
                    if v_align == 'c':
                        # 中心對齊：文字上移 text_height/2，需要額外空間
                        final_height = text_height + text_height // 2
                    elif v_align == 'b':
                        # 底部對齊：文字上移 text_height，需要雙倍空間
                        final_height = text_height * 2

                if len(align_state) >= 2:
                    h_align = align_state[1]
                    if h_align == 'c':
                        final_width = text_width + text_width // 2
                    elif h_align == 'r':
                        final_width = text_width * 2

                # 設定最小大小，確保文字不會被截斷
                self.setMinimumSize(max(final_width, 20), max(final_height, 20))
                self.resize(max(final_width, 20), max(final_height, 20))
                self.update()

            def connect(self, key, external_signal, external_method=None):
                if key not in self.attributes:
                    raise NameError(f"{key} not in attribute")
                internal_signal = getattr(self, "_" + key, False)
                internal_method = getattr(self, key, False)

                def set_value(value):
                    if internal_method:
                        self.attributes[key] = value
                        internal_method(value)
                    else:
                        print(f"WARNING: implementation {key} methods may be required")

                external_signal.connect(set_value)
                if external_method is not None and internal_signal:
                    internal_signal.connect(external_method)

            def get_attributes(self):
                return self.attributes

            def paintEvent(self, event):
                """
                統一處理 alignment 偏移、rotation 旋轉和 skew 變換
                - alignment: 決定繪製錨點 (tl, tc, tr, cl, cc, cr, bl, bc, br)
                - rotation: 以物件座標原點為軸旋轉 (0-360 度)
                - skew_x: y 軸順時針旋轉角度 (-90 ~ 90)，圖形變成平行四邊形
                - skew_y: x 軸順時針旋轉角度 (-90 ~ 90)
                """
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)

                # 安全獲取屬性值（沒有這些屬性的物件使用預設值）
                align_state = getattr(self, '_align_state', 'tl')
                rotation = getattr(self, '_rotation_angle', 0)
                skew_x = getattr(self, '_skew_x_value', 0)
                skew_y = getattr(self, '_skew_y_value', 0)

                # 限制 skew 範圍並檢查是否消失
                skew_x = max(-90, min(90, skew_x))
                skew_y = max(-90, min(90, skew_y))
                if abs(skew_x) >= 90 or abs(skew_y) >= 90:
                    painter.end()
                    return

                # 使用文字實際大小計算偏移量（而不是 Label 大小）
                text_w = getattr(self, '_text_render_width', self.width())
                text_h = getattr(self, '_text_render_height', self.height())

                # 根據 alignment 計算偏移量
                # 第一個字符: 垂直對齊 (t=top, c=center, b=bottom)
                # 第二個字符: 水平對齊 (l=left, c=center, r=right)
                offset_x, offset_y = 0, 0

                if len(align_state) >= 1:
                    v_align = align_state[0]
                    if v_align == 'c':
                        offset_y = -text_h / 2
                    elif v_align == 'b':
                        offset_y = -text_h
                    # 't' 不需要偏移

                if len(align_state) >= 2:
                    h_align = align_state[1]
                    if h_align == 'c':
                        offset_x = -text_w / 2
                    elif h_align == 'r':
                        offset_x = -text_w
                    # 'l' 不需要偏移

                # 建立變換矩陣
                transform = QTransform()

                # 1. 先根據 alignment 偏移原點
                transform.translate(offset_x, offset_y)

                # 2. 應用 rotation 旋轉（以物件座標原點為軸）
                transform.rotate(rotation)

                # 3. 應用 skew 變換
                # skew_x: y 軸順時針旋轉，使用 shear 的水平分量
                # skew_y: x 軸順時針旋轉，使用 shear 的垂直分量
                # shear(sh, sv): x' = x + sh*y, y' = sv*x + y
                shear_h = math.tan(math.radians(skew_x))
                shear_v = math.tan(math.radians(skew_y))
                transform.shear(shear_h, shear_v)

                painter.setTransform(transform)

                # 呼叫子類的繪製方法
                self._drawContent(painter)

                painter.end()

            def _drawContent(self, painter):
                """繪製文字內容"""
                # 取得文字顏色
                color = getattr(self, '_color_value', 'ffffff')
                painter.setPen(QColor(f"#{color}"))

                # 取得字型 (使用 QLabel.font 避免呼叫自訂的 font() 方法)
                font = QLabel.font(self)
                painter.setFont(font)

                # 使用文字實際大小作為繪製區域
                text_w = getattr(self, '_text_render_width', self.width())
                text_h = getattr(self, '_text_render_height', self.height())
                rect = QRect(0, 0, text_w, text_h)

                # 繪製文字
                text = self._text_value if hasattr(self, '_text_value') else ''
                painter.drawText(rect, Qt.AlignCenter, text)

            def validity_testing(self,value,typ):
                try:
                    return typ(value)
                except:
                    return self.compilation(value)
                
            def compilation(self,script):
                return None

            # Text 專屬方法
            def text(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._text_value = value
                    self.setText(value)
                    self._adjustSize()
                    self._text.emit(value)
                return self._text_value

            def text_size(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._text_size_value = value
                    self.set_font_size(value)
                    self._adjustSize()
                    self._text_size.emit(value)
                return self._text_size_value

            def font(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._font_value = value
                    self.set_font(value)
                    self._adjustSize()
                    self._font.emit(value)
                return self._font_value

            def transform(self, value=None):
                value = self.validity_testing(value, str)
                if value is None:
                    return self._transform_value
                self._transform_value = value
                if value == "n":
                    self.setText(self._text_value)
                if value == "u":
                    self.setText(self._text_value.upper())
                if value == "l":
                    self.setText(self._text_value.lower())
                self._transform.emit(value)
                return self._transform_value

            def name(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._name_value = value
                    self._name.emit(value)
                return self._name_value

            # Position 方法
            def x(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.move(value, self.pos().y())
                    self._x.emit(value)
                return self.pos().x()

            def y(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self.move(self.pos().x(), value)
                    self._y.emit(value)
                return self.pos().y()

            def rotation(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._rotation_angle = value
                    self.update()
                    self._rotation.emit(value)
                return self._rotation_angle

            def opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._opacity_effect.setOpacity(value * 0.01)
                    self.setGraphicsEffect(self._opacity_effect)
                    self._opacity.emit(value)
                return self._opacity_effect.opacity()

            def alignment(self, value=None):
                value = self.validity_testing(value, str)
                if value is None:
                    return self._align_state
                self._align_state = value
                self._adjustSize()
                self._alignment.emit(value)
                return self._align_state

            # Transform 方法
            def gyro(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._gyro_value = value
                    self.update()
                    self._gyro.emit(value)
                return self._gyro_value

            def skew_x(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._skew_x_value = max(-90, min(90, value))
                    self.update()
                    self._skew_x.emit(value)
                return self._skew_x_value

            def skew_y(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._skew_y_value = max(-90, min(90, value))
                    self.update()
                    self._skew_y.emit(value)
                return self._skew_y_value

            def scale_x(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._scale_x_value = value
                    self.update()
                    self._scale_x.emit(value)
                return self._scale_x_value

            def scale_y(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._scale_y_value = value
                    self.update()
                    self._scale_y.emit(value)
                return self._scale_y_value

            # Color 方法
            def color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._color_value = value
                    self._color.emit(value)
                return self._color_value

            def color_dim(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._color_dim_value = value
                    self._color_dim.emit(value)
                return self._color_dim_value

            # Display 方法
            def display(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._display_value = value
                    self._display.emit(value)
                return self._display_value

            # Interaction 方法
            def tap_action(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._tap_action_value = value
                    self._tap_action.emit(value)
                return self._tap_action_value

            # AnimScale 方法
            def anim_scale_x(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._anim_scale_x_value = value
                    self._anim_scale_x.emit(value)
                return self._anim_scale_x_value

            def anim_scale_y(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._anim_scale_y_value = value
                    self._anim_scale_y.emit(value)
                return self._anim_scale_y_value

            # Shadow 方法
            def shadow(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._shadow_value = value
                    self._shadow.emit(value)
                return self._shadow_value

            def w_color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._w_color_value = value
                    self._w_color.emit(value)
                return self._w_color_value

            def w_distance(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._w_distance_value = value
                    self._w_distance.emit(value)
                return self._w_distance_value

            def w_opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._w_opacity_value = value
                    self._w_opacity.emit(value)
                return self._w_opacity_value

            # Outline 方法
            def outline(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._outline_value = value
                    self._outline.emit(value)
                return self._outline_value

            def o_color(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._o_color_value = value
                    self._o_color.emit(value)
                return self._o_color_value

            def o_size(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._o_size_value = value
                    self._o_size.emit(value)
                return self._o_size_value

            def o_opacity(self, value=None):
                value = self.validity_testing(value, int)
                if value is not None:
                    self._o_opacity_value = value
                    self._o_opacity.emit(value)
                return self._o_opacity_value

            # Shader 方法
            def shader(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._shader_value = value
                    self._shader.emit(value)
                return self._shader_value

            def u_1(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_1_value = value
                    self._u_1.emit(value)
                return self._u_1_value

            def u_2(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_2_value = value
                    self._u_2.emit(value)
                return self._u_2_value

            def u_3(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_3_value = value
                    self._u_3.emit(value)
                return self._u_3_value

            def u_4(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_4_value = value
                    self._u_4.emit(value)
                return self._u_4_value

            def u_5(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._u_5_value = value
                    self._u_5.emit(value)
                return self._u_5_value

            # Blend 方法
            def blend_mode(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._blend_mode_value = value
                    self._blend_mode.emit(value)
                return self._blend_mode_value

        _component_classes[component_type] = Text
        return Text(attribute)

    elif component_type == "image":
        class Image(*tuple(bases)):
            _path = pyqtSignal(object)
            _name = pyqtSignal(object)

            def __init__(self, attributes=None, parent=None):
                # 呼叫第一個 base 類別的 __init__（最終會呼叫 Component.__init__）
                super().__init__(attributes, parent)

                # 呼叫所有 common 類別的 _init_xxx 方法
                _init_all_commons(self, common_types)

                # Image 專屬屬性
                self._path_value = ""
                self._name_value = "Image Layer"

            def path(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._path_value = value
                    self._path.emit(value)
                return self._path_value

            def name(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._name_value = value
                    self._name.emit(value)
                return self._name_value

        _component_classes[component_type] = Image
        return Image(attribute)

    elif component_type == "shape":
        class Shape(*tuple(bases)):
            _shape = pyqtSignal(object)
            _name = pyqtSignal(object)

            def __init__(self, attributes=None, parent=None):
                super().__init__(attributes, parent)

                # 呼叫所有 common 類別的 _init_xxx 方法
                _init_all_commons(self, common_types)

                # Shape 專屬屬性
                self._shape_value = "Square"
                self._name_value = "Shape Layer"

            def shape(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._shape_value = value
                    self._shape.emit(value)
                return self._shape_value

            def name(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._name_value = value
                    self._name.emit(value)
                return self._name_value

        _component_classes[component_type] = Shape
        return Shape(attribute)

    elif component_type == "group":
        class Group(*tuple(bases)):
            _name = pyqtSignal(object)

            def __init__(self, attributes=None, parent=None):
                super().__init__(attributes, parent)

                # 呼叫所有 common 類別的 _init_xxx 方法
                _init_all_commons(self, common_types)

                # Group 專屬屬性
                self._name_value = "Group"

            def name(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._name_value = value
                    self._name.emit(value)
                return self._name_value

        _component_classes[component_type] = Group
        return Group(attribute)

    else:
        # 通用的 component 類別（用到再擴充）
        # 捕獲 component_type 到閉包中
        _ct = component_type

        class GenericComponent(*tuple(bases)):
            _name = pyqtSignal(object)

            def __init__(self, attributes=None, parent=None):
                super().__init__(attributes, parent)

                # 呼叫所有 common 類別的 _init_xxx 方法
                _init_all_commons(self, common_types)

                # GenericComponent 專屬屬性
                self._name_value = _ct

            def name(self, value=None):
                value = self.validity_testing(value, str)
                if value is not None:
                    self._name_value = value
                    self._name.emit(value)
                return self._name_value

        _component_classes[component_type] = GenericComponent
        return GenericComponent(attribute)
