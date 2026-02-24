"""
Components module with lazy loading support.
元件模組，支援延遲載入。
"""

import importlib
from typing import TYPE_CHECKING
import copy

# 定義可延遲載入的屬性
_lazy_imports = {
    # common.py - layer type definitions (圖層類型定義)
    'baseLayer': 'common',
    'animationWidget': 'common',
    'textLayer': 'common',
    'directionalLightLayer': 'common',
    'layer3D': 'common',
    'curvedTextLayer': 'common',
    'imageLayer': 'common',
    'tachymeterLayer': 'common',
    'shapeLayer': 'common',
    'markerLayer': 'common',
    'mapLayer': 'common',
    'slideshowLayer': 'common',
    'textRingLayer': 'common',
    'roundedRectangleLayer': 'common',
    'seriesLayer': 'common',
    'complicationLayer': 'common',
    'chartLayer': 'common',
    'imageCondLayer': 'common',
    'imageGifLayer': 'common',
    'progressLayer': 'common',
    'ringLayer': 'common',
    'markersHMLayer': 'common',
    # attributes.py - object definitions (物件定義與預設值)
    'watchSetting': 'attributes',
    'watchBackground': 'attributes',
    'text': 'attributes',
    'light': 'attributes',
    'photoCube': 'attributes',
    'textCurved': 'attributes',
    'minuteHand': 'attributes',
    'hourHand': 'attributes',
    'secondHand': 'attributes',
    'battery': 'attributes',
    'wifi': 'attributes',
    'event': 'attributes',
    'countdown': 'attributes',
    'tachy': 'attributes',
    'weather': 'attributes',
    'shape': 'attributes',
    'marker': 'attributes',
    'map': 'attributes',
    'compass': 'attributes',
    'date': 'attributes',
    'steps': 'attributes',
    'moon': 'attributes',
    'model3d': 'attributes',
    'slideshow': 'attributes',
    'numbers': 'attributes',
    'hourMinMarkers': 'attributes',
    'rounded': 'attributes',
    'series': 'attributes',
    'time': 'attributes',
    'stopWatch1': 'attributes',
    'stopWatch2': 'attributes',
    'stopWatch3': 'attributes',
    'complication': 'attributes',
    'chart': 'attributes',
    'imageGif': 'attributes',
    'progress': 'attributes',
    'ring': 'attributes',
    # utils.py
    'summon_components': 'utils',
}

# 快取已載入的模組
_loaded_modules = {}

def __getattr__(name: str):
    """延遲載入屬性"""
    if name in _lazy_imports:
        module_name = _lazy_imports[name]

        # 檢查模組是否已載入
        if module_name not in _loaded_modules:
            _loaded_modules[module_name] = importlib.import_module(
                f'.{module_name}', __name__
            )

        return copy.deepcopy(getattr(_loaded_modules[module_name], name))

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """列出所有可用屬性"""
    return list(_lazy_imports.keys())


# 為了 IDE 自動完成和類型檢查 (不會實際執行載入)
if TYPE_CHECKING:
    from .common import (
        baseLayer,
        animationWidget,
        textLayer,
        directionalLightLayer,
        layer3D,
        curvedTextLayer,
        imageLayer,
        tachymeterLayer,
        shapeLayer,
        markerLayer,
        mapLayer,
        slideshowLayer,
        textRingLayer,
        roundedRectangleLayer,
        seriesLayer,
        complicationLayer,
        chartLayer,
        imageCondLayer,
        imageGifLayer,
        progressLayer,
        ringLayer,
        markersHMLayer,
    )
    from .attributes import (
        watchSetting,
        watchBackground,
        text,
        light,
        photoCube,
        textCurved,
        minuteHand,
        hourHand,
        secondHand,
        battery,
        wifi,
        event,
        countdown,
        tachy,
        weather,
        shape,
        marker,
        map,
        compass,
        date,
        steps,
        moon,
        model3d,
        slideshow,
        numbers,
        hourMinMarkers,
        rounded,
        series,
        time,
        stopWatch1,
        stopWatch2,
        stopWatch3,
        complication,
        chart,
        imageGif,
        progress,
        ring,
    )
    from .utils import summon_components


__all__ = list(_lazy_imports.keys())
