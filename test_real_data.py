#!/usr/bin/env python3
import sys
import os

# 添加專案路徑
sys.path.insert(0, '/Users/lishengfeng/Desktop/Highway_trafficwave')

from datetime import datetime
from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem

def test_real_traffic_data():
    """測試真實的交通資料獲取"""
    print("🔧 測試真實交通資料獲取...")
    
    try:
        # 初始化資料收集系統
        data_system = OptimizedIntegratedDataCollectionSystem()
        
        # 獲取最新的即時資料
        latest_data = data_system.get_latest_data_for_shockwave()
        
        current_time = datetime.now()
        stations = []
        
        print(f"📊 資料狀態: {latest_data is not None}")
        if latest_data is not None:
            print(f"📊 資料筆數: {len(latest_data) if hasattr(latest_data, '__len__') else 'N/A'}")
            print(f"📊 資料是否為空: {latest_data.empty if hasattr(latest_data, 'empty') else 'N/A'}")
        
        if latest_data is not None and not latest_data.empty:
            print("✅ 找到真實資料！")
            print("資料欄位:", list(latest_data.columns))
            print("前3筆資料:")
            print(latest_data.head(3))
            
            # 轉換真實資料為 API 格式
            for idx, row in latest_data.iterrows():
                try:
                    station_data = {
                        "id": str(row.get('station_id', idx)),
                        "name": row.get('station_name', f"監測站 {idx}"),
                        "latitude": float(row.get('latitude', 25.0)),
                        "longitude": float(row.get('longitude', 121.0)),
                        "flow": float(row.get('volume', 0)) if row.get('volume') else 0,
                        "speed": float(row.get('speed', 0)) if row.get('speed') else 0,
                        "timestamp": current_time.isoformat()
                    }
                    stations.append(station_data)
                    print(f"✅ 處理站點: {station_data['name']}")
                except Exception as e:
                    print(f"⚠️ 跳過問題資料行 {idx}: {e}")
                    continue
            
            print(f"\n📊 總共處理了 {len(stations)} 個站點")
            
        else:
            print("⚠️ 沒有真實資料，這是預期的結果（TDX 需要時間收集資料）")
            
        # 模擬 API 回應
        if not stations:
            result = {
                "stations": [],
                "total_count": 0,
                "last_updated": current_time.isoformat(),
                "message": "正在等待 TDX 即時交通資料...",
                "data_source": "TDX_realtime",
                "status": "waiting_for_data",
                "note": "台北站和桃園站的虛擬資料已移除，系統正在收集真實交通數據"
            }
        else:
            result = {
                "stations": stations,
                "total_count": len(stations),
                "last_updated": current_time.isoformat(),
                "data_source": "TDX_realtime"
            }
        
        print("\n🎯 API 回應預覽:")
        print(f"站點數量: {result['total_count']}")
        print(f"資料來源: {result['data_source']}")
        print(f"狀態: {result.get('status', 'normal')}")
        if result.get('message'):
            print(f"訊息: {result['message']}")
            
        return result
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_real_traffic_data()