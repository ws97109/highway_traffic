#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MT-STNet 整合測試腳本
測試MT-STNet即時預測系統的完整功能
"""

import sys
import os
import requests
import json
from datetime import datetime

def test_mt_stnet_predictor():
    """測試MT-STNet預測器"""
    print("🔍 測試 MT-STNet 預測器...")
    
    try:
        # 導入MT-STNet預測器
        sys.path.append('src/models/mt_stnet')
        from src.models.mt_stnet.realtime_predictor import MTSTNetRealtimePredictor
        
        # 初始化預測器
        predictor = MTSTNetRealtimePredictor()
        print("✅ MT-STNet 預測器初始化成功")
        
        # 測試模型載入
        model_loaded = predictor.load_model()
        if model_loaded:
            print("✅ 模型載入成功")
        else:
            print("⚠️ 模型載入失敗，將使用簡化預測")
        
        # 測試系統狀態
        status = predictor.get_system_status()
        print(f"📊 系統狀態:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # 測試單次預測
        print("\n🔮 執行單次預測測試...")
        result = predictor.run_single_prediction()
        
        if result.get('predictions'):
            print(f"✅ 預測成功: {len(result['predictions'])} 個站點")
            print(f"📊 模型版本: {result.get('model_version', 'N/A')}")
            print(f"⏰ 預測時間: {result.get('prediction_time', 'N/A')}")
            
            # 顯示前3個預測結果
            print("\n📋 預測結果預覽:")
            for i, pred in enumerate(result['predictions'][:3]):
                print(f"   {i+1}. {pred['location_name']}")
                print(f"      流量: {pred['predicted_flow']:.1f} 輛/h")
                print(f"      速度: {pred['predicted_speed']:.1f} km/h")
                print(f"      信心度: {pred['confidence']:.2f}")
        else:
            print(f"❌ 預測失敗: {result.get('error', '未知錯誤')}")
        
        return True
        
    except Exception as e:
        print(f"❌ MT-STNet 預測器測試失敗: {e}")
        return False

def test_api_endpoints():
    """測試API端點"""
    print("\n🌐 測試 API 端點...")
    
    base_url = "http://localhost:8000"  # 假設API運行在8000端口
    
    endpoints = [
        "/api/prediction/traffic",
        "/api/prediction/model/status",
        "/api/prediction/accuracy"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"📡 測試 {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint} 回應正常")
                
                if endpoint == "/api/prediction/traffic":
                    predictions = data.get('predictions', [])
                    print(f"   📊 預測結果: {len(predictions)} 個站點")
                    if predictions:
                        print(f"   🏷️ 模型版本: {data.get('model_version', 'N/A')}")
                        print(f"   📈 資料來源: {data.get('data_source', 'N/A')}")
                
                elif endpoint == "/api/prediction/model/status":
                    print(f"   🤖 模型名稱: {data.get('model_name', 'N/A')}")
                    print(f"   📊 狀態: {data.get('status', 'N/A')}")
                    print(f"   🎯 目標站點: {data.get('target_stations_count', 0)}")
                
            else:
                print(f"⚠️ {endpoint} 回應異常: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint} 連接失敗 - API服務器可能未運行")
        except Exception as e:
            print(f"❌ {endpoint} 測試失敗: {e}")

def test_data_collection():
    """測試資料收集系統"""
    print("\n📊 測試資料收集系統...")
    
    try:
        from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem
        
        # 初始化資料收集系統
        collector = OptimizedIntegratedDataCollectionSystem(base_dir="data")
        print("✅ 資料收集系統初始化成功")
        
        # 測試系統功能
        success = collector.test_optimized_system()
        if success:
            print("✅ 資料收集系統測試通過")
        else:
            print("⚠️ 資料收集系統測試部分失敗")
        
        return True
        
    except Exception as e:
        print(f"❌ 資料收集系統測試失敗: {e}")
        return False

def test_frontend_integration():
    """測試前端整合"""
    print("\n🖥️ 測試前端整合...")
    
    # 檢查前端組件檔案
    frontend_files = [
        "frontend/src/components/prediction/MTSTNetPredictor.tsx",
        "frontend/src/pages/admin/ControlCenter.tsx"
    ]
    
    for file_path in frontend_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
    
    # 檢查API路由
    api_file = "api/routes/prediction.py"
    if os.path.exists(api_file):
        print(f"✅ {api_file} 存在")
        
        # 檢查是否包含MT-STNet相關代碼
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'MTSTNetRealtimePredictor' in content:
                print("✅ API路由已整合MT-STNet預測器")
            else:
                print("⚠️ API路由未整合MT-STNet預測器")
    else:
        print(f"❌ {api_file} 不存在")

def generate_test_report():
    """生成測試報告"""
    print("\n📋 生成測試報告...")
    
    report = {
        "test_time": datetime.now().isoformat(),
        "test_results": {
            "mt_stnet_predictor": "需要執行測試",
            "api_endpoints": "需要執行測試", 
            "data_collection": "需要執行測試",
            "frontend_integration": "需要執行測試"
        },
        "recommendations": [
            "確保TDX和TISC API憑證正確配置",
            "檢查資料目錄結構是否完整",
            "驗證前端組件是否正確導入",
            "測試API服務器是否正常運行"
        ]
    }
    
    # 保存報告
    report_file = f"mt_stnet_test_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 測試報告已保存: {report_file}")

def main():
    """主函數"""
    print("=" * 60)
    print("🚀 MT-STNet 整合測試")
    print("=" * 60)
    
    print("📝 測試項目:")
    print("1. MT-STNet 預測器功能")
    print("2. API 端點回應")
    print("3. 資料收集系統")
    print("4. 前端整合檢查")
    
    print("\n選擇測試模式:")
    print("1. 完整測試")
    print("2. 僅測試預測器")
    print("3. 僅測試API")
    print("4. 僅測試資料收集")
    print("5. 僅測試前端整合")
    print("6. 生成測試報告")
    
    try:
        choice = input("\n請選擇 (1-6): ").strip()
        
        if choice == "1":
            print("\n🔄 執行完整測試...")
            test_mt_stnet_predictor()
            test_api_endpoints()
            test_data_collection()
            test_frontend_integration()
            generate_test_report()
            
        elif choice == "2":
            test_mt_stnet_predictor()
            
        elif choice == "3":
            test_api_endpoints()
            
        elif choice == "4":
            test_data_collection()
            
        elif choice == "5":
            test_frontend_integration()
            
        elif choice == "6":
            generate_test_report()
            
        else:
            print("❌ 無效選擇")
    
    except KeyboardInterrupt:
        print("\n🛑 測試被中斷")
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 測試完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
