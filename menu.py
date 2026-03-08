"""
菜單欄模組

包含應用程序的菜單欄和相關功能
"""

import os
from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QAction,
    QFileDialog,
    QMenu,
    QHBoxLayout,
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QSizePolicy,
    QFrame,
)
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QCursor, QPixmap, QDesktopServices
from PyQt5.QtCore import QUrl
from common import FlowLayout


def load_style():
    """載入菜單樣式"""
    style_path = os.path.join(os.path.dirname(__file__), "style", "menu.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Style file not found: {style_path}")
        return ""


class MenuBar(QWidget):
    """自定義菜單欄類"""

    # 定義信號
    file_imported = pyqtSignal(str)  # 當文件被導入時發出信號，傳遞文件路徑

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("menuBar")
        self.setFixedHeight(30)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(load_style())
        self.setup_ui()
        self.setup_menus()

    def setup_ui(self):
        """設置UI佈局"""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignLeft)

    def setup_menus(self):
        """設置所有菜單"""
        self.create_file_menu()
        self.create_about_menu()

    def create_file_menu(self):
        """創建 File 菜單"""
        # 創建 File 按鈕
        self.file_button = QPushButton("File")
        self.file_button.setObjectName("menuButton")
        self.file_button.setFixedHeight(30)

        # 創建下拉菜單
        self.file_menu = QMenu(self)
        self.file_menu.setObjectName("fileMenu")

        # Import 動作
        self.import_action = QAction("Import", self)
        self.import_action.setShortcut("Ctrl+I")
        self.import_action.setStatusTip("Import a watch file")
        self.import_action.triggered.connect(self.import_file)
        self.file_menu.addAction(self.import_action)

        # 可以在這裡添加更多菜單項
        # 例如：
        # self.file_menu.addSeparator()
        # export_action = QAction("Export", self)
        # export_action.setShortcut("Ctrl+E")
        # self.file_menu.addAction(export_action)

        # 綁定按鈕點擊事件
        self.file_button.clicked.connect(self.show_file_menu)

        # 添加到佈局
        self.layout.addWidget(self.file_button)

    def create_about_menu(self):
        """創建 About 菜單"""
        self.about_button = QPushButton("About")
        self.about_button.setObjectName("menuButton")
        self.about_button.setFixedHeight(30)

        self.about_menu = QMenu(self)
        self.about_menu.setObjectName("fileMenu")

        self.icon_source_action = QAction("Icon Source", self)
        self.icon_source_action.triggered.connect(self.show_icon_source_dialog)
        self.about_menu.addAction(self.icon_source_action)

        self.about_button.clicked.connect(self.show_about_menu)

        self.layout.addWidget(self.about_button)

    def show_about_menu(self):
        """顯示 About 菜單"""
        button_pos = self.about_button.mapToGlobal(
            self.about_button.rect().bottomLeft()
        )
        self.about_menu.exec_(button_pos)

    def show_icon_source_dialog(self):
        """顯示 Icon Source 對話框"""
        dialog = IconSourceDialog(self.parent_window)
        dialog.exec_()

    def show_file_menu(self):
        """顯示 File 菜單"""
        # 在按鈕下方顯示菜單
        button_pos = self.file_button.mapToGlobal(self.file_button.rect().bottomLeft())
        self.file_menu.exec_(button_pos)

    def import_file(self):
        """打開文件選擇對話框"""
        file_dialog = QFileDialog(self.parent_window)
        file_dialog.setWindowTitle("Import Watch File")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Watch Files (*.watch);;All Files (*)")

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                print(f"Selected file: {file_path}")
                # 發出信號通知主窗口
                self.file_imported.emit(file_path)
                # 返回文件路徑
                return file_path
        return None


class IconSourceDialog(QDialog):
    """顯示 img/icon 目錄中所有圖示的對話框"""

    ICON_SIZE = 64  # 圖示顯示大小 (px)
    ICON_LABEL_GAP = 6  # 圖示與名稱之間的間距
    CELL_PADDING = 12  # 每個 cell 的內部 padding
    DIALOG_WIDTH = 520
    DIALOG_HEIGHT = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Icon Source")
        self.setObjectName("iconSourceDialog")
        self.setFixedSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(load_style())
        self._setup_ui()
        self._load_icons()

    def _setup_ui(self):
        """建立對話框 UI"""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- 可捲動區域 ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("iconScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        # 內容容器 + FlowLayout
        self.content_widget = QWidget()
        self.content_widget.setObjectName("iconContentWidget")
        self.flow_layout = FlowLayout(self.content_widget)
        self.flow_layout.setContentsMargins(12, 12, 12, 12)
        self.flow_layout.setSpacing(8)
        self.scroll_area.setWidget(self.content_widget)

        root_layout.addWidget(self.scroll_area, stretch=1)

        # --- 分隔線 ---
        separator = QFrame()
        separator.setObjectName("iconDialogSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setFixedHeight(1)
        root_layout.addWidget(separator)

        # --- 底部署名 ---
        attribution = QLabel()
        attribution.setObjectName("iconAttribution")
        attribution.setText(
            'Uicons by <a href="https://www.flaticon.com/uicons" '
            'style="color:#4db8ff;">Flaticon</a>'
        )
        attribution.setOpenExternalLinks(True)
        attribution.setAlignment(Qt.AlignCenter)
        attribution.setFixedHeight(36)
        root_layout.addWidget(attribution)

    def _load_icons(self):
        """從 img/icon 目錄讀取所有圖示並加入 FlowLayout"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_dir = os.path.join(base_dir, "img", "icon")

        if not os.path.isdir(icon_dir):
            return

        supported = (".png", ".jpg", ".jpeg", ".svg", ".bmp")
        files = sorted(f for f in os.listdir(icon_dir) if f.lower().endswith(supported))

        for filename in files:
            filepath = os.path.join(icon_dir, filename)
            cell = self._make_icon_cell(filepath, filename)
            self.flow_layout.addWidget(cell)

    def _make_icon_cell(self, filepath: str, filename: str) -> QWidget:
        """為單個圖示建立 cell widget（圖示 + 檔名標籤）"""
        name_no_ext = os.path.splitext(filename)[0]

        cell = QWidget()
        cell.setObjectName("iconCell")

        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(
            self.CELL_PADDING, self.CELL_PADDING, self.CELL_PADDING, self.CELL_PADDING
        )
        cell_layout.setSpacing(self.ICON_LABEL_GAP)
        cell_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # 圖示
        icon_label = QLabel()
        icon_label.setObjectName("iconImage")
        icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        icon_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.ICON_SIZE,
                self.ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            icon_label.setPixmap(scaled)
        else:
            icon_label.setText("?")

        # 檔名標籤
        name_label = QLabel(name_no_ext)
        name_label.setObjectName("iconName")
        name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(self.ICON_SIZE + self.CELL_PADDING * 2)

        cell_layout.addWidget(icon_label, alignment=Qt.AlignHCenter)
        cell_layout.addWidget(name_label)

        # 固定 cell 寬度，讓 FlowLayout 能正確排列
        cell_w = self.ICON_SIZE + self.CELL_PADDING * 2
        cell.setFixedWidth(cell_w)

        return cell
