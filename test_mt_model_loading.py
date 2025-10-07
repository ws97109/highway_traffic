#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 MT-STNet 模型載入
"""

import sys
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.mt_stnet.realtime_predictor import MTSTNetRealtimePredictor

def test_model_loading():
    """測試模型載入"""
    print("=" * 60)
    print("測試 MT-STNet 模型載入")
    print("=" * 60)

    try:
        # 初始化預測器
        print("\n1. 初始化預測器...")
        predictor = MTSTNetRealtimePredictor()
        print("✅ 預測器初始化成功")

        # 載入模型
        print("\n2. 載入 MT-STNet 模型...")
        success = predictor.load_model()

        if success and predictor.is_model_loaded:
            print("✅ 模型載入成功！")
            print(f"   - 模型已載入: {predictor.is_model_loaded}")
            print(f"   - TensorFlow session: {'已建立' if predictor.sess else '未建立'}")
            print(f"   - 正規化參數: mean={predictor.normalization_params['mean']:.2f}, std={predictor.normalization_params['std']:.2f}")
        else:
            print("⚠️ 模型載入失敗，將使用簡化預測邏輯")
            print(f"   - 模型已載入: {predictor.is_model_loaded}")

        # 檢查系統狀態
        print("\n3. 系統狀態:")
        status = predictor.get_system_status()
        for key, value in status.items():
            print(f"   - {key}: {value}")

        # 清理
        print("\n4. 清理資源...")
        if predictor.sess:
            predictor.sess.close()
            print("✅ Session 已關閉")

        print("\n" + "=" * 60)
        print("測試完成")
        print("=" * 60)

        return success

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)
