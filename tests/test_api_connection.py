#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API連接測試腳本
測試前端是否能正確連接到後端API
"""

import requests
import json
from datetime import datetime

def test_api_endpoints():
    """測試API端點"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/traffic/current",
        "/api/shockwave/active", 
        "/api/admin/system-status",
        "/api/admin/traffic-metrics",
        "/api/admin/recommended-actions",
        "/api/prediction/traffic",
        "/api/prediction/model/status"
    ]
    
    print("🌐 測試API連接...")
    print(f"📡 基礎URL: {base_url}")
    print("=" * 50)
    
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint in endpoints:
        try:
            print(f"📡 測試 {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint} - 狀態碼: {response.status_code}")
                
                # 顯示部分回應內容
                if isinstance(data, dict):
                    if 'predictions' in data:
                        print(f"   📊 預測結果: {len(data.get('predictions', []))} 個")
                    elif 'shockwaves' in data:
                        print(f"   🌊 震波數量: {len(data.get('shockwaves', []))}")
                    elif 'model_name' in data:
                        print(f"   🤖 模型: {data.get('model_name', 'N/A')}")
                    elif 'overallHealth' in data:
                        print(f"   💚 系統健康: {data.get('overallHealth', 'N/A')}")
                    else:
                        print(f"   📋 資料鍵: {list(data.keys())[:3]}")
                elif isinstance(data, list):
                    print(f"   📋 陣列長度: {len(data)}")
                
                success_count += 1
                
            else:
                print(f"⚠️ {endpoint} - 狀態碼: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint} - 連接失敗 (ECONNREFUSED)")
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint} - 請求超時")
        except Exception as e:
            print(f"❌ {endpoint} - 錯誤: {e}")
        
        print()
    
    print("=" * 50)
    print(f"📊 測試結果: {success_count}/{total_count} 成功")
    success_rate = (success_count / total_count) * 100
    print(f"📈 成功率: {success_rate:.1f}%")
    
    if success_count == total_count:
        print("🎉 所有API端點都正常工作！")
        print("✅ 前端應該能夠正常連接到後端")
    elif success_count > 0:
        print("⚠️ 部分API端點工作正常")
        print("💡 建議檢查失敗的端點")
    else:
        print("❌ 無法連接到API服務器")
        print("💡 請確認:")
        print("   1. API服務器是否在運行 (python api/main.py)")
        print("   2. 服務器是否監聽在 localhost:8000")
        print("   3. 防火牆是否阻擋連接")
    
    return success_rate >= 50

def test_mt_stnet_prediction():
    """專門測試MT-STNet預測端點"""
    print("\n🔮 專門測試MT-STNet預測...")
    
    try:
        url = "http://localhost:8000/api/prediction/traffic"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ MT-STNet預測API正常")
            
            if 'predictions' in data:
                predictions = data['predictions']
                print(f"📊 預測站點數: {len(predictions)}")
                print(f"🏷️ 模型版本: {data.get('model_version', 'N/A')}")
                print(f"📈 資料來源: {data.get('data_source', 'N/A')}")
                
                if predictions:
                    print("\n📋 前3個預測結果:")
                    for i, pred in enumerate(predictions[:3]):
                        print(f"   {i+1}. {pred.get('location_name', 'N/A')}")
                        print(f"      流量: {pred.get('predicted_flow', 0):.1f} 輛/h")
                        print(f"      速度: {pred.get('predicted_speed', 0):.1f} km/h")
                        print(f"      信心度: {pred.get('confidence', 0):.2f}")
                
                return True
            else:
                print("⚠️ 回應中沒有預測資料")
                return False
        else:
            print(f"❌ HTTP錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ MT-STNet預測測試失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 API連接測試")
    print(f"⏰ 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 基本API測試
    api_success = test_api_endpoints()
    
    # MT-STNet專門測試
    mt_stnet_success = test_mt_stnet_prediction()
    
    print("\n" + "=" * 50)
    print("📋 測試總結:")
    print(f"   API連接: {'✅ 正常' if api_success else '❌ 異常'}")
    print(f"   MT-STNet: {'✅ 正常' if mt_stnet_success else '❌ 異常'}")
    
    if api_success and mt_stnet_success:
        print("\n🎉 恭喜！API服務器完全正常")
        print("💡 如果前端仍有問題，請嘗試:")
        print("   1. 重新啟動前端服務器")
        print("   2. 清除瀏覽器快取")
        print("   3. 檢查瀏覽器控制台錯誤")
    else:
        print("\n⚠️ 發現問題，請檢查API服務器狀態")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
