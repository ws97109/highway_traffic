"""
簡化測試演示 - 直接驗證代號轉換和駕駛建議功能
"""

import os
import sys
import asyncio
from pathlib import Path
from loguru import logger

# 添加項目路徑
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 導入增強的模組
from train_model.data_processing.enhanced_csv_processor import EnhancedHighwayCSVProcessor
from train_model.models.ollama_client import OllamaClient
from train_model.models.driver_advisor import IntelligentDriverAdvisor

async def demo_code_to_name_conversion():
    """演示代號轉換功能"""
    print("="*50)
    print("🔄 代號轉換演示")
    print("="*50)
    
    try:
        config_path = current_dir.parent / "configs" / "rag_config.yaml"
        processor = EnhancedHighwayCSVProcessor(str(config_path))
        
        # 測試各種代號轉換
        test_codes = [
            "N0010_SB,034K+000",
            "N0010_NB,037K+600", 
            "N0030_SB,079K+000",
            "N0030_NB,132K+500"
        ]
        
        print("\n📍 代號轉換結果：")
        for code in test_codes:
            friendly_name = processor.resolve_station_code(code)
            print(f"   原代號: {code}")
            print(f"   友善名稱: {friendly_name}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 代號轉換測試失敗: {e}")
        return False

def demo_enhanced_description():
    """演示增強描述功能"""
    print("="*50) 
    print("📝 增強描述演示")
    print("="*50)
    
    try:
        config_path = current_dir.parent / "configs" / "rag_config.yaml"
        processor = EnhancedHighwayCSVProcessor(str(config_path))
        
        # 載入少量樣本資料
        highway1_df, highway3_df = processor.load_highway_data()
        sample1 = highway1_df.head(2)
        sample3 = highway3_df.head(2)
        
        print("\n🛣️ 國道1號範例描述:")
        descriptions1 = processor.generate_enhanced_text_descriptions(sample1)
        if descriptions1:
            print(descriptions1[0][:800] + "...")
            
        print("\n🛣️ 國道3號範例描述:")
        descriptions3 = processor.generate_enhanced_text_descriptions(sample3)
        if descriptions3:
            print(descriptions3[0][:800] + "...")
            
        return True
        
    except Exception as e:
        print(f"❌ 增強描述測試失敗: {e}")
        return False

def demo_rest_areas():
    """演示休息站功能"""
    print("="*50)
    print("🏨 休息站資訊演示") 
    print("="*50)
    
    try:
        config_path = current_dir.parent / "configs" / "rag_config.yaml"
        processor = EnhancedHighwayCSVProcessor(str(config_path))
        
        # 測試休息站查找
        test_locations = [
            ("01F", 60.0),  # 國道1號60公里處
            ("03F", 100.0)  # 國道3號100公里處
        ]
        
        for highway_code, mileage in test_locations:
            highway_name = "國道1號" if highway_code == "01F" else "國道3號"
            print(f"\n🚗 {highway_name} {mileage}公里處附近休息站:")
            
            rest_areas = processor.find_nearby_rest_areas(highway_code, mileage)
            if rest_areas:
                for area in rest_areas[:3]:
                    direction = "前方" if area['is_ahead'] else "後方"
                    print(f"   📍 {area['name']}: {direction} {area['distance_km']:.1f}公里")
                    print(f"      設施: {', '.join(area['facilities'])}")
            else:
                print("   ℹ️ 附近暫無休息站資訊")
                
        return True
        
    except Exception as e:
        print(f"❌ 休息站測試失敗: {e}")
        return False

async def demo_simple_ollama_chat():
    """演示基本 Ollama 聊天功能"""
    print("="*50)
    print("🤖 Ollama 聊天演示")
    print("="*50)
    
    try:
        config_path = current_dir.parent / "configs" / "rag_config.yaml"
        ollama_client = OllamaClient(str(config_path))
        
        if not await ollama_client.check_connection():
            print("❌ Ollama 服務未運行")
            return False
            
        print("✅ Ollama 服務連接正常")
        
        # 測試基本對話
        test_questions = [
            "你好，請簡單介紹台灣的高速公路系統",
            "如果在高速公路上遇到塞車，一般有什麼應對方法？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n💬 測試問題 {i}: {question}")
            try:
                response = await ollama_client.generate_response(question)
                print(f"🤖 回答: {response[:300]}...")
                print(f"   (完整回答長度: {len(response)} 字符)")
            except Exception as e:
                print(f"❌ 回答失敗: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ Ollama 聊天測試失敗: {e}")
        return False

async def demo_driver_advisor():
    """演示駕駛建議系統"""
    print("="*50)
    print("🚗 駕駛建議系統演示")
    print("="*50)
    
    try:
        config_path = current_dir.parent / "configs" / "rag_config.yaml"
        advisor = IntelligentDriverAdvisor(str(config_path))
        await advisor.initialize()
        
        print("✅ 駕駛建議系統初始化成功")
        
        # 模擬駕駛情境
        from train_model.models.driver_advisor import TrafficCondition, ShockwaveAlert
        from datetime import datetime, timedelta
        
        current_location = {
            'highway': '國道1號',
            'direction': '南向',
            'mileage': 55.5,
            'station_id': '01F0555S',
            'friendly_name': '湖口交流道附近',
            'lat': 24.123456,
            'lng': 121.123456
        }
        
        destination = {
            'name': '台中市',
            'distance_km': 150,
            'estimated_time_min': 120
        }
        
        # 測試不同交通狀況
        traffic_scenarios = [
            {
                'name': '正常狀況',
                'data': TrafficCondition(
                    station_id='01F0555S',
                    speed=85.0,
                    flow=800,
                    travel_time=5.0,
                    congestion_level='smooth',
                    timestamp=datetime.now()
                ),
                'alert': None
            },
            {
                'name': '輕度壅塞',
                'data': TrafficCondition(
                    station_id='01F0555S',
                    speed=45.0,
                    flow=1200,
                    travel_time=8.5,
                    congestion_level='congested',
                    timestamp=datetime.now()
                ),
                'alert': None
            },
            {
                'name': '嚴重壅塞+震波預警',
                'data': TrafficCondition(
                    station_id='01F0555S',
                    speed=25.0,
                    flow=1500,
                    travel_time=12.0,
                    congestion_level='severe',
                    timestamp=datetime.now()
                ),
                'alert': ShockwaveAlert(
                    intensity=8.5,
                    propagation_speed=20.0,
                    estimated_arrival=datetime.now() + timedelta(minutes=10),
                    affected_area='湖口至新竹段',
                    warning_level='severe'
                )
            }
        ]
        
        for scenario in traffic_scenarios:
            print(f"\n📊 情境: {scenario['name']}")
            print(f"   當前車速: {scenario['data'].speed} km/h")
            print(f"   壅塞程度: {scenario['data'].congestion_level}")
            
            try:
                advice = await advisor.analyze_current_situation(
                    current_location, destination, scenario['data'], scenario['alert']
                )
                
                print(f"🎯 建議:")
                print(f"   優先級: {advice.priority}")
                print(f"   行動類型: {advice.action_type}")
                print(f"   標題: {advice.title}")
                print(f"   描述: {advice.description[:200]}...")
                print(f"   安全評估: {advice.safety_impact}")
                
                if advice.rest_areas:
                    print(f"   附近休息站: {len(advice.rest_areas)} 個")
                    for area in advice.rest_areas[:2]:
                        print(f"     • {area.name} ({area.direction} {area.distance_km:.1f}km)")
                        
                if advice.alternatives:
                    print(f"   替代路線: {len(advice.alternatives)} 條")
                    for alt in advice.alternatives[:2]:
                        print(f"     • {alt.route_name}: {alt.description[:100]}...")
                        
            except Exception as e:
                print(f"❌ 建議生成失敗: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ 駕駛建議系統測試失敗: {e}")
        return False

async def main():
    """主演示函數"""
    print("🚗 智能駕駛建議系統功能演示")
    print("🔧 此演示將測試各個核心功能模組")
    print()
    
    results = {}
    
    # 1. 代號轉換演示
    print("測試 1/5: 代號轉換功能...")
    results['code_conversion'] = await demo_code_to_name_conversion()
    
    # 2. 增強描述演示  
    print("\n測試 2/5: 增強描述功能...")
    results['enhanced_description'] = demo_enhanced_description()
    
    # 3. 休息站功能演示
    print("\n測試 3/5: 休息站資訊...")
    results['rest_areas'] = demo_rest_areas()
    
    # 4. Ollama 聊天演示
    print("\n測試 4/5: Ollama 聊天功能...")
    results['ollama_chat'] = await demo_simple_ollama_chat()
    
    # 5. 駕駛建議系統演示
    print("\n測試 5/5: 駕駛建議系統...")
    results['driver_advisor'] = await demo_driver_advisor()
    
    # 顯示總結
    print("\n" + "="*50)
    print("📋 測試結果總結")
    print("="*50)
    
    for test_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        test_display = {
            'code_conversion': '代號轉換',
            'enhanced_description': '增強描述', 
            'rest_areas': '休息站資訊',
            'ollama_chat': 'Ollama 聊天',
            'driver_advisor': '駕駛建議系統'
        }
        print(f"{test_display.get(test_name, test_name)}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n🎯 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count >= 4:
        print("🎉 系統基本功能正常，增強功能已成功實現！")
        print()
        print("💡 主要改進:")
        print("   ✅ 代號自動轉換為友善名稱")
        print("   ✅ 詳細路段描述和駕駛提醒")
        print("   ✅ 休息站資訊整合")
        print("   ✅ 智能駕駛建議生成")
        print("   ✅ 多情境交通分析")
    else:
        print("⚠️ 部分功能需要進一步調整")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())