#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Highway Traffic System - Environment Check Script
高速公路交通系統 - 環境檢查腳本

檢查所有必要的 Python 套件是否正確安裝和配置
"""

import sys
import os
from datetime import datetime

def check_package(package_name, import_name=None, version_attr='__version__'):
    """檢查套件是否可以導入並獲取版本"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = __import__(import_name)
        version = getattr(module, version_attr, 'Unknown')
        return True, version
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print("="*70)
    print("🚀 Highway Traffic System - Environment Check")
    print("高速公路交通衝擊波檢測與預測系統 - 環境檢查")
    print("="*70)
    print(f"檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python 版本: {sys.version}")
    print(f"Python 路徑: {sys.executable}")
    print("="*70)
    
    # 核心數據科學套件
    core_packages = [
        ('numpy', 'numpy'),
        ('pandas', 'pandas'),
        ('scipy', 'scipy'),
        ('matplotlib', 'matplotlib'),
        ('seaborn', 'seaborn'),
        ('scikit-learn', 'sklearn'),
    ]
    
    # 深度學習套件
    ml_packages = [
        ('tensorflow', 'tensorflow'),
        ('torch', 'torch'),
        ('torchvision', 'torchvision'),
    ]
    
    # 圖形和網路套件
    graph_packages = [
        ('networkx', 'networkx'),
        ('plotly', 'plotly'),
    ]
    
    # Web 和 API 套件
    web_packages = [
        ('flask', 'flask'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('requests', 'requests'),
    ]
    
    # 資料庫套件
    db_packages = [
        ('sqlalchemy', 'sqlalchemy'),
        ('h5py', 'h5py'),
        ('tables', 'tables'),
        ('sqlite3', 'sqlite3', None),  # 內建模組無版本
    ]
    
    # GIS 和地理套件
    gis_packages = [
        ('geopandas', 'geopandas'),
        ('folium', 'folium'),
    ]
    
    # 視覺化套件
    viz_packages = [
        ('opencv-python', 'cv2'),
        ('bokeh', 'bokeh'),
        ('dash', 'dash'),
    ]
    
    # 工具套件
    utility_packages = [
        ('tqdm', 'tqdm'),
        ('psutil', 'psutil'),
        ('python-dotenv', 'dotenv'),
        ('rich', 'rich'),
        ('click', 'click'),
        ('redis', 'redis'),
    ]
    
    # 電子郵件套件
    email_packages = [
        ('yagmail', 'yagmail'),
    ]
    
    all_packages = [
        ("🔬 核心數據科學套件", core_packages),
        ("🤖 機器學習/深度學習套件", ml_packages),
        ("📊 圖形和網路分析套件", graph_packages),
        ("🌐 Web 和 API 套件", web_packages),
        ("🗄️ 資料庫套件", db_packages),
        ("🗺️ GIS 和地理套件", gis_packages),
        ("📈 視覺化套件", viz_packages),
        ("🔧 工具套件", utility_packages),
        ("📧 電子郵件套件", email_packages),
    ]
    
    total_packages = 0
    successful_packages = 0
    failed_packages = []
    
    for category_name, packages in all_packages:
        print(f"\n{category_name}")
        print("-" * 50)
        
        for package_info in packages:
            if len(package_info) == 2:
                package_name, import_name = package_info
                version_attr = '__version__'
            elif len(package_info) == 3:
                package_name, import_name, version_attr = package_info
            else:
                package_name = import_name = package_info[0]
                version_attr = '__version__'
            
            total_packages += 1
            success, version = check_package(package_name, import_name, version_attr)
            
            if success:
                status = "✅"
                successful_packages += 1
                version_info = f"v{version}" if version != 'Unknown' and version else ""
            else:
                status = "❌"
                failed_packages.append((package_name, version))
                version_info = f"Error: {version}"
            
            print(f"{status} {package_name:<20} {version_info}")
    
    # 總結
    print("\n" + "="*50)
    print("📋 檢查總結")
    print("="*50)
    print(f"總套件數量: {total_packages}")
    print(f"成功安裝: {successful_packages}")
    print(f"安裝失敗: {len(failed_packages)}")
    print(f"成功率: {(successful_packages/total_packages)*100:.1f}%")
    
    if failed_packages:
        print("\n❌ 安裝失敗的套件:")
        for package, error in failed_packages:
            print(f"  - {package}: {error}")
    
    # MT-STNet 特定測試
    print("\n" + "="*50)
    print("🧠 MT-STNet 深度學習模型測試")
    print("="*50)
    
    try:
        import tensorflow as tf
        import numpy as np
        import pandas as pd
        
        # 測試 TensorFlow 計算
        test_tensor = tf.random.normal([10, 10])
        result = tf.reduce_sum(test_tensor)
        print("✅ TensorFlow 計算測試通過")
        
        # 測試 numpy 相容性
        test_array = np.random.random((5, 5))
        print("✅ NumPy 陣列操作測試通過")
        
        # 測試 pandas 資料操作
        test_df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        print("✅ Pandas 資料操作測試通過")
        
        print("🎉 MT-STNet 環境完全就緒！")
        
    except Exception as e:
        print(f"❌ MT-STNet 環境測試失敗: {e}")
    
    # 環境建議
    print("\n" + "="*50)
    print("💡 環境建議")
    print("="*50)
    
    if len(failed_packages) == 0:
        print("🎉 所有套件都已正確安裝！您的環境已準備就緒。")
        print("\n可以開始使用以下功能:")
        print("  • 高速公路交通數據分析")
        print("  • MT-STNet 深度學習模型訓練")
        print("  • 即時交通衝擊波檢測")
        print("  • 交通流量預測")
        print("  • 視覺化和報告生成")
    else:
        print("⚠️  有部分套件未正確安裝，建議執行:")
        print("conda activate highway-traffic-system")
        print("pip install --upgrade", " ".join([pkg for pkg, _ in failed_packages]))
    
    print("\n" + "="*70)
    print("檢查完成 - Environment Check Complete!")
    print("="*70)

if __name__ == "__main__":
    main()
