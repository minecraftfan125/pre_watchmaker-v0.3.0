"""Watch Face Text 元件

提供可自訂字型的文字標籤元件，用於顯示錶面上的文字。
支援兩種字型格式：
1. TTF/OTF 向量字型
2. BMFont 點陣圖字型 (.fnt + .png)
"""

import os
import re
from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QFontDatabase, QColor, QPixmap, QPainter, QImage


class BMFontChar:
    """BMFont 單個字元資訊"""
    def __init__(self):
        self.id = 0          # 字元 ID (ASCII/Unicode)
        self.x = 0           # 在圖片中的 X 座標
        self.y = 0           # 在圖片中的 Y 座標
        self.width = 0       # 字元寬度
        self.height = 0      # 字元高度
        self.xoffset = 0     # 繪製時的 X 偏移
        self.yoffset = 0     # 繪製時的 Y 偏移
        self.xadvance = 0    # 繪製下一個字元時的水平前進量
        self.page = 0        # 所在頁面 ID
        self.chnl = 0        # 通道


class BMFont:
    """BMFont 點陣圖字型解析器"""

    def __init__(self, fnt_path):
        """載入 BMFont 字型

        Args:
            fnt_path: .fnt 檔案路徑
        """
        self.fnt_path = fnt_path
        self.base_dir = os.path.dirname(fnt_path)

        # 字型資訊
        self.face = ""
        self.size = 0
        self.bold = False
        self.italic = False

        # 共用資訊
        self.line_height = 0
        self.base = 0
        self.scale_w = 0
        self.scale_h = 0

        # 頁面圖片
        self.pages = {}  # page_id -> QPixmap

        # 字元映射
        self.chars = {}  # char_id -> BMFontChar

        # 字距調整
        self.kernings = {}  # (first, second) -> amount

        # 解析 .fnt 檔案
        self._parse_fnt()

    def _parse_fnt(self):
        """解析 .fnt 檔案"""
        try:
            with open(self.fnt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith('info '):
                        self._parse_info(line)
                    elif line.startswith('common '):
                        self._parse_common(line)
                    elif line.startswith('page '):
                        self._parse_page(line)
                    elif line.startswith('char '):
                        self._parse_char(line)
                    elif line.startswith('kerning '):
                        self._parse_kerning(line)
        except Exception as e:
            print(f"Error parsing BMFont file {self.fnt_path}: {e}")

    def _parse_value(self, line, key):
        """從行中解析指定 key 的值"""
        # 匹配 key=value 或 key="value"
        pattern = rf'{key}=(?:"([^"]*)"|(\S+))'
        match = re.search(pattern, line)
        if match:
            return match.group(1) if match.group(1) is not None else match.group(2)
        return None

    def _parse_int(self, line, key, default=0):
        """解析整數值"""
        value = self._parse_value(line, key)
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default

    def _parse_info(self, line):
        """解析 info 行"""
        self.face = self._parse_value(line, 'face') or ""
        self.size = self._parse_int(line, 'size')
        self.bold = self._parse_int(line, 'bold') == 1
        self.italic = self._parse_int(line, 'italic') == 1

    def _parse_common(self, line):
        """解析 common 行"""
        self.line_height = self._parse_int(line, 'lineHeight')
        self.base = self._parse_int(line, 'base')
        self.scale_w = self._parse_int(line, 'scaleW')
        self.scale_h = self._parse_int(line, 'scaleH')

    def _parse_page(self, line):
        """解析 page 行並載入圖片"""
        page_id = self._parse_int(line, 'id')
        filename = self._parse_value(line, 'file')

        if filename:
            # 移除可能的引號
            filename = filename.strip('"')
            image_path = os.path.join(self.base_dir, filename)

            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.pages[page_id] = pixmap
                else:
                    print(f"Warning: Failed to load BMFont image: {image_path}")
            else:
                print(f"Warning: BMFont image not found: {image_path}")

    def _parse_char(self, line):
        """解析 char 行"""
        char = BMFontChar()
        char.id = self._parse_int(line, 'id')
        char.x = self._parse_int(line, 'x')
        char.y = self._parse_int(line, 'y')
        char.width = self._parse_int(line, 'width')
        char.height = self._parse_int(line, 'height')
        char.xoffset = self._parse_int(line, 'xoffset')
        char.yoffset = self._parse_int(line, 'yoffset')
        char.xadvance = self._parse_int(line, 'xadvance')
        char.page = self._parse_int(line, 'page')
        char.chnl = self._parse_int(line, 'chnl')

        self.chars[char.id] = char

    def _parse_kerning(self, line):
        """解析 kerning 行"""
        first = self._parse_int(line, 'first')
        second = self._parse_int(line, 'second')
        amount = self._parse_int(line, 'amount')
        self.kernings[(first, second)] = amount

    def get_kerning(self, first_char, second_char):
        """取得兩個字元之間的字距調整值"""
        first_id = ord(first_char) if isinstance(first_char, str) else first_char
        second_id = ord(second_char) if isinstance(second_char, str) else second_char
        return self.kernings.get((first_id, second_id), 0)

    def get_char(self, char):
        """取得字元資訊"""
        char_id = ord(char) if isinstance(char, str) else char
        return self.chars.get(char_id)

    def measure_text(self, text, scale=1.0):
        """測量文字尺寸

        Args:
            text: 要測量的文字
            scale: 縮放比例

        Returns:
            (width, height) 元組
        """
        if not text:
            return (0, 0)

        width = 0
        height = self.line_height * scale

        prev_char = None
        for char in text:
            char_info = self.get_char(char)
            if char_info:
                # 加上字距調整
                if prev_char:
                    width += self.get_kerning(prev_char, char) * scale

                width += char_info.xadvance * scale
            prev_char = char

        return (int(width), int(height))

    def render_text(self, text, scale=1.0, color=None):
        """渲染文字為 QPixmap

        Args:
            text: 要渲染的文字
            scale: 縮放比例
            color: 文字顏色 (QColor)，若為 None 則使用原始顏色

        Returns:
            QPixmap
        """
        if not text or not self.pages:
            return QPixmap()

        # 計算文字尺寸
        width, height = self.measure_text(text, scale)
        if width <= 0 or height <= 0:
            return QPixmap()

        # 建立透明背景的圖片
        result = QPixmap(width, height)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 繪製每個字元
        x = 0
        prev_char = None

        for char in text:
            char_info = self.get_char(char)
            if not char_info:
                prev_char = char
                continue

            # 字距調整
            if prev_char:
                x += self.get_kerning(prev_char, char) * scale

            # 取得頁面圖片
            page_pixmap = self.pages.get(char_info.page)
            if page_pixmap:
                # 來源區域
                src_rect = QRect(
                    char_info.x,
                    char_info.y,
                    char_info.width,
                    char_info.height
                )

                # 目標區域
                dst_x = x + char_info.xoffset * scale
                dst_y = char_info.yoffset * scale
                dst_rect = QRect(
                    int(dst_x),
                    int(dst_y),
                    int(char_info.width * scale),
                    int(char_info.height * scale)
                )

                # 繪製字元
                painter.drawPixmap(dst_rect, page_pixmap, src_rect)

            x += char_info.xadvance * scale
            prev_char = char

        painter.end()

        # 如果指定了顏色，對圖片進行著色
        if color and color.isValid():
            result = self._colorize_pixmap(result, color)

        return result

    def _colorize_pixmap(self, pixmap, color):
        """對 pixmap 進行著色，保留透明度"""
        if pixmap.isNull():
            return pixmap

        # 轉換為 QImage 以便逐像素處理
        image = pixmap.toImage()
        image = image.convertToFormat(QImage.Format_ARGB32)

        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixelColor(x, y)
                if pixel.alpha() > 0:
                    # 保留原始亮度作為新顏色的強度
                    gray = (pixel.red() + pixel.green() + pixel.blue()) // 3
                    intensity = gray / 255.0

                    new_color = QColor(
                        int(color.red() * intensity),
                        int(color.green() * intensity),
                        int(color.blue() * intensity),
                        pixel.alpha()
                    )
                    image.setPixelColor(x, y, new_color)

        return QPixmap.fromImage(image)


class FontManager:
    """字型管理器，負責載入和管理自訂字型"""

    _instance = None
    _fonts_loaded = False
    _font_families = {}   # 字型檔名 -> 字型家族名稱 的映射 (TTF)
    _bmfonts = {}         # 字型檔名 -> BMFont 實例 的映射

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not FontManager._fonts_loaded:
            self._load_fonts()
            FontManager._fonts_loaded = True

    def _load_fonts(self):
        """載入 font 目錄中的所有字型"""
        # 取得 font 目錄路徑
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(base_dir, "font")

        if not os.path.exists(font_dir):
            print(f"Warning: Font directory not found: {font_dir}")
            return

        # 遍歷 font 目錄中的所有檔案
        for filename in os.listdir(font_dir):
            filepath = os.path.join(font_dir, filename)

            if filename.lower().endswith(('.ttf', '.otf')):
                # 載入 TTF/OTF 字型
                self._load_ttf_font(filepath, filename)
            elif filename.lower().endswith('.fnt'):
                # 載入 BMFont 字型
                self._load_bmfont(filepath, filename)

    def _load_ttf_font(self, font_path, filename):
        """載入 TTF/OTF 字型檔案"""
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id == -1:
            print(f"Warning: Failed to load font: {font_path}")
            return

        # 取得字型家族名稱
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family_name = families[0]
            # 使用不含副檔名的檔名作為 key
            font_key = os.path.splitext(filename)[0]
            FontManager._font_families[font_key] = family_name
            FontManager._font_families[filename] = family_name

    def _load_bmfont(self, fnt_path, filename):
        """載入 BMFont 字型"""
        try:
            bmfont = BMFont(fnt_path)
            if bmfont.pages:  # 確保至少有一個頁面載入成功
                font_key = os.path.splitext(filename)[0]
                FontManager._bmfonts[font_key] = bmfont
                FontManager._bmfonts[filename] = bmfont
        except Exception as e:
            print(f"Warning: Failed to load BMFont: {fnt_path}, {e}")

    def get_font_family(self, font_name):
        """根據字型名稱取得 TTF 字型家族名稱"""
        if font_name in FontManager._font_families:
            return FontManager._font_families[font_name]

        font_name_lower = font_name.lower()
        for key, family in FontManager._font_families.items():
            if key.lower() == font_name_lower:
                return family

        return None

    def get_bmfont(self, font_name):
        """根據字型名稱取得 BMFont 實例"""
        if font_name in FontManager._bmfonts:
            return FontManager._bmfonts[font_name]

        font_name_lower = font_name.lower()
        for key, bmfont in FontManager._bmfonts.items():
            if key.lower() == font_name_lower:
                return bmfont

        return None

    def is_bmfont(self, font_name):
        """檢查字型是否為 BMFont 格式"""
        return self.get_bmfont(font_name) is not None

    def get_available_fonts(self):
        """取得所有可用字型的列表"""
        fonts = set()

        # TTF 字型
        for key in FontManager._font_families.keys():
            if not key.lower().endswith(('.ttf', '.otf')):
                fonts.add(key)

        # BMFont 字型
        for key in FontManager._bmfonts.keys():
            if not key.lower().endswith('.fnt'):
                fonts.add(key)

        return sorted(list(fonts))

    def get_ttf_fonts(self):
        """取得所有 TTF 字型列表"""
        return sorted([k for k in FontManager._font_families.keys()
                      if not k.lower().endswith(('.ttf', '.otf'))])

    def get_bitmap_fonts(self):
        """取得所有 BMFont 字型列表"""
        return sorted([k for k in FontManager._bmfonts.keys()
                      if not k.lower().endswith('.fnt')])

    def get_font(self, font_name, size=12):
        """取得 QFont 物件（僅適用於 TTF 字型）"""
        family = self.get_font_family(font_name)
        if family:
            return QFont(family, size)
        else:
            return QFont("Arial", size)


class Watch_Face_Text(QLabel):
    """錶面文字元件

    支援自訂字型、顏色、大小等屬性的文字標籤。
    可使用 TTF 向量字型或 BMFont 點陣圖字型。

    Signals:
        text_changed: 文字內容改變時發出
        font_changed: 字型改變時發出
    """

    text_changed = pyqtSignal(str)
    font_changed = pyqtSignal(str)

    def __init__(self, text="", parent=None):
        """初始化 Watch_Face_Text

        Args:
            text: 初始文字內容
            parent: 父元件
        """
        super().__init__(parent)

        # 初始化字型管理器
        self._font_manager = FontManager()

        # 預設屬性
        self._text = text
        self._font_name = ""
        self._font_size = 12
        self._font_scale = 1.0  # BMFont 縮放比例
        self._text_color = QColor(255, 255, 255)
        self._is_bmfont = False
        self._bmfont = None

        # 設定基本樣式
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: transparent;")

        # 設定初始文字
        if text:
            super().setText(text)

    def set_font(self, font_name, size=None):
        """設定字型

        Args:
            font_name: 字型檔名（來自 font 目錄）
            size: 字型大小（TTF）或縮放比例（BMFont，1.0 = 原始大小）
        """
        self._font_name = font_name

        # 檢查是否為 BMFont
        bmfont = self._font_manager.get_bmfont(font_name)

        if bmfont:
            # BMFont 模式
            self._is_bmfont = True
            self._bmfont = bmfont

            if size is not None:
                # 對於 BMFont，size 參數作為縮放因子
                # 如果 size 較大（如 48），計算相對於原始大小的比例
                if size > 10:
                    self._font_scale = size / bmfont.size if bmfont.size > 0 else 1.0
                else:
                    self._font_scale = size
            else:
                self._font_scale = 1.0

            self._update_bmfont_display()
        else:
            # TTF 模式
            self._is_bmfont = False
            self._bmfont = None

            if size is not None:
                self._font_size = size

            font = self._font_manager.get_font(font_name, self._font_size)
            super().setFont(font)

        self.font_changed.emit(font_name)

    def set_font_size(self, size):
        """設定字型大小

        Args:
            size: 字型大小（TTF）或縮放比例（BMFont）
        """
        if self._is_bmfont:
            if self._bmfont and size > 10:
                self._font_scale = size / self._bmfont.size if self._bmfont.size > 0 else 1.0
            else:
                self._font_scale = size
            self._update_bmfont_display()
        else:
            self._font_size = size
            if self._font_name:
                self.set_font(self._font_name, size)
            else:
                font = QLabel.font(self)  # 使用 QLabel.font() 避免被子類覆蓋
                font.setPointSize(size)
                super().setFont(font)

    def set_text_color(self, color):
        """設定文字顏色

        Args:
            color: QColor 或顏色字串（如 "#FFFFFF" 或 "white"）
        """
        if isinstance(color, str):
            self._text_color = QColor(color)
        elif isinstance(color, QColor):
            self._text_color = color
        else:
            return

        if self._is_bmfont:
            self._update_bmfont_display()
        else:
            self.setStyleSheet(f"color: {self._text_color.name()}; background-color: transparent;")

    def setText(self, text):
        """設定文字內容

        Args:
            text: 文字內容
        """
        self._text = text

        if self._is_bmfont:
            self._update_bmfont_display()
        else:
            super().setText(text)

        self.text_changed.emit(text)

    def text(self):
        """取得文字內容"""
        return self._text

    def _update_bmfont_display(self):
        """更新 BMFont 顯示"""
        if not self._bmfont or not self._text:
            super().setText("")
            self.setPixmap(QPixmap())
            return

        # 渲染文字
        pixmap = self._bmfont.render_text(
            self._text,
            self._font_scale,
            self._text_color
        )

        if not pixmap.isNull():
            self.setPixmap(pixmap)
        else:
            super().setText(self._text)

    def get_font_name(self):
        """取得當前字型名稱"""
        return self._font_name

    def get_font_size(self):
        """取得當前字型大小"""
        return self._font_size if not self._is_bmfont else self._font_scale

    def get_text_color(self):
        """取得當前文字顏色"""
        return self._text_color

    def is_bitmap_font(self):
        """檢查是否使用 BMFont"""
        return self._is_bmfont

    @staticmethod
    def get_available_fonts():
        """取得所有可用字型列表

        Returns:
            list: 可用字型名稱列表
        """
        return FontManager().get_available_fonts()

    @staticmethod
    def get_ttf_fonts():
        """取得所有 TTF 字型列表"""
        return FontManager().get_ttf_fonts()

    @staticmethod
    def get_bitmap_fonts():
        """取得所有 BMFont 字型列表"""
        return FontManager().get_bitmap_fonts()
