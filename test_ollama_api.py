#!/usr/bin/env python3
import requests
import json

def test_ollama_direct():
    """測試直接調用 Ollama"""
    print("🔧 測試直接調用 Ollama...")
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5:7b",
        "prompt": "你好，請分析當前交通狀況並提供建議。",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 200
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.ok:
            result = response.json()
            print("✅ Ollama 直接調用成功!")
            print(f"回應: {result.get('response', '無回應')[:100]}...")
            return True
        else:
            print(f"❌ Ollama 調用失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama 連接錯誤: {e}")
        return False

def test_traffic_api():
    """測試交通數據 API"""
    print("\n🚗 測試交通數據 API...")
    
    try:
        response = requests.get("http://localhost:8000/api/traffic/current", timeout=10)
        if response.ok:
            data = response.json()
            print(f"✅ 交通數據獲取成功! 站點數: {len(data.get('stations', []))}")
            return data
        else:
            print(f"❌ 交通數據獲取失敗: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 交通數據 API 錯誤: {e}")
        return None

def test_integrated_chat():
    """測試整合的聊天功能"""
    print("\n🤖 測試整合聊天功能...")
    
    # 獲取交通數據
    traffic_data = test_traffic_api()
    
    # 模擬交通數據分析請求
    url = "http://localhost:11434/api/generate"
    
    # 構建包含交通數據的提示
    if traffic_data:
        stations = traffic_data.get('stations', [])
        total_stations = len(stations)
        avg_speed = sum(s.get('speed', 0) for s in stations) / total_stations if total_stations > 0 else 0
        
        traffic_summary = f"""
當前交通狀況：
- 監測站點: {total_stations} 個
- 平均車速: {avg_speed:.1f} km/h
- 更新時間: {traffic_data.get('last_updated', '未知')}
"""
        
        prompt = f"""你是一個專業的交通分析助手，請根據以下即時交通數據提供駕駛建議：

{traffic_summary}

用戶問題：目前路況如何？有什麼駕駛建議？

請用繁體中文回答，提供具體且實用的建議。"""
    else:
        prompt = "你是交通助手，目前沒有即時數據，請提供一般性的駕駛安全建議。"
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 300
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.ok:
            result = response.json()
            print("✅ 整合聊天測試成功!")
            print("🤖 AI 回應:")
            print(result.get('response', '無回應'))
            return True
        else:
            print(f"❌ 整合聊天失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 整合聊天錯誤: {e}")
        return False

if __name__ == "__main__":
    print("🚀 開始測試 Ollama 整合功能...\n")
    
    # 測試各個組件
    ollama_ok = test_ollama_direct()
    traffic_ok = test_traffic_api() is not None
    chat_ok = test_integrated_chat()
    
    print(f"\n📊 測試結果總結:")
    print(f"- Ollama 服務: {'✅' if ollama_ok else '❌'}")
    print(f"- 交通數據 API: {'✅' if traffic_ok else '❌'}")
    print(f"- 整合聊天功能: {'✅' if chat_ok else '❌'}")
    
    if ollama_ok and traffic_ok and chat_ok:
        print("\n🎉 所有測試通過！可以開始整合前端。")
    else:
        print("\n⚠️ 部分測試失敗，需要修復後再繼續。")