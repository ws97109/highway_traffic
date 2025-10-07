#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試完整的 MT-STNet 預測流程"""

import sys
import os

# 設定路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("測試完整 MT-STNet 預測流程")
print("=" * 60)

try:
    print("\n1. 導入模組...")
    from src.models.mt_stnet.realtime_predictor import MTSTNetRealtimePredictor
    import numpy as np
    print("✅ 模組導入成功")

    print("\n2. 初始化並載入模型...")
    predictor = MTSTNetRealtimePredictor()
    success = predictor.load_model()

    if not success or not predictor.is_model_loaded:
        print("❌ 模型載入失敗")
        sys.exit(1)

    print(f"✅ 模型載入成功")
    print(f"   - Session: {predictor.sess is not None}")
    print(f"   - Model: {predictor.model is not None}")

    print("\n3. 創建測試資料...")
    # 創建假資料用於測試
    import pandas as pd
    from datetime import datetime, timedelta

    stations = predictor.target_stations[:10]  # 使用前10個站點測試
    test_data = []
    base_time = datetime.now()

    for i in range(12):  # 12個時間步
        time = base_time - timedelta(minutes=5*i)
        for station in stations:
            test_data.append({
                'station': station,
                'timestamp': time,
                'flow': np.random.randint(100, 500),
                'median_speed': np.random.uniform(60, 90),
                'avg_travel_time': np.random.uniform(5, 15)
            })

    test_df = pd.DataFrame(test_data)
    print(f"✅ 測試資料創建完成: {len(test_df)} 筆記錄")

    print("\n4. 預處理資料...")
    processed = predictor.preprocess_data_for_prediction(test_df)

    if processed is None:
        print("❌ 資料預處理失敗")
        sys.exit(1)

    print("✅ 資料預處理成功")
    print(f"   - features shape: {processed['features'].shape}")
    print(f"   - x_all shape: {processed['x_all'].shape}")
    print(f"   - day_of_week shape: {processed['day_of_week'].shape}")
    print(f"   - minute_of_day shape: {processed['minute_of_day'].shape}")
    print(f"   - 站點數: {len(processed['station_list'])}")

    print("\n5. 執行預測...")
    predictions = predictor.predict_traffic(processed, processed['station_list'])

    if 'error' in predictions:
        print(f"❌ 預測失敗: {predictions['error']}")
        sys.exit(1)

    print("✅ 預測成功！")
    print(f"   - 預測站點數: {predictions['total_stations']}")
    print(f"   - 資料來源: {predictions['data_source']}")
    print(f"   - 時間範圍: {predictions['time_horizon_minutes']} 分鐘")

    print("\n6. 預測結果範例（前3個站點）:")
    for i, pred in enumerate(predictions['predictions'][:3]):
        print(f"\n   站點 {i+1}: {pred['location_name']}")
        print(f"      - 預測流量: {pred['predicted_flow']:.1f}")
        print(f"      - 預測速度: {pred['predicted_speed']:.1f} km/h")
        print(f"      - 信心度: {pred['confidence']:.2%}")

    # 清理
    if predictor.sess:
        predictor.sess.close()
        print("\n✅ Session 已關閉")

    print("\n" + "=" * 60)
    print("🎉 測試完全成功！MT-STNet 模型正常運作！")
    print("=" * 60)
    print("\n✅ 現在可以重啟 main.py，系統將使用真正的 MT-STNet 模型！")

except Exception as e:
    print(f"\n❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
