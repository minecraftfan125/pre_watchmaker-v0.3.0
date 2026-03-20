from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QMimeData,
    QRect,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt5.QtGui import (
    QPixmap,
    QDrag,
)

def Dragable(emitdata: str):
    def change_method(cls):
        def do_nothing(*args, **kwargs):
            pass

        original_mousePress = getattr(cls, "mousePressEvent", do_nothing)
        original_mouseMove = getattr(cls, "mouseMoveEvent", do_nothing)
        original_mouseRelease = getattr(cls, "mouseReleaseEvent", do_nothing)

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
            tmp = QWidget()
            drag = QDrag(tmp)
            mime_data = QMimeData()
            # 存储组件信息（tooltip）
            mime_data.setText(getattr(self, emitdata))
            drag.setMimeData(mime_data)
            # 执行拖拽
            drag.exec_(Qt.CopyAction)
            # 重置拖拽起始位置
            self.drag_start_position = None
            self.draged = True
            self.mouseReleaseEvent(event)

        def mouseReleaseEvent(self, event):
            if self.draged is False:
                original_mousePress(self, event)
            self.draged = False
            original_mouseRelease(self, event)

        cls.mousePressEvent = mousePressEvent
        cls.mouseMoveEvent = mouseMoveEvent
        cls.mouseReleaseEvent = mouseReleaseEvent
        return cls

    return change_method

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
