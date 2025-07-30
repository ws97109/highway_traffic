"""
交通衝擊波檢測與預測系統
Highway Traffic Shock Wave Detection and Prediction System

主要模組:
- core: 核心系統
- detection: 衝擊波檢測
- prediction: 衝擊波預測
- data: 資料處理
- utils: 工具函數
- systems: 系統功能
"""

__version__ = "1.0.0"
__author__ = "timwei0801"

# 導入主要模組
from . import core
from . import detection
from . import prediction
from . import data
from . import utils
from . import systems

__all__ = [
    'core',
    'detection', 
    'prediction',
    'data',
    'utils',
    'systems'
]
