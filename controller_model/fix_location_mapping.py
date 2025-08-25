#!/usr/bin/env python3
"""
修復地名映射問題
將里程數轉換為友善地名
"""

import json
import sys
import os
sys.path.append('/Users/tommy/Desktop/Highway_trafficwave')

def create_mileage_to_location_mapping():
    """創建里程數到地名的映射"""
    # 基於 Etag.csv 和實際路段的地名映射
    location_mapping = {
        # 國道一號北向
        (34, 38): "五股段",
        (38, 42): "林口段", 
        (42, 47): "桃園段",
        (47, 52): "機場系統段",
        (52, 58): "中壢段",
        (58, 64): "內壢段",
        (64, 69): "平鎮楊梅段",
        (69, 75): "幼獅校前段",
        (75, 88): "湖口段",
        (88, 93): "竹北段",
        (93, 98): "新竹段",
        (98, 105): "頭份段",
        
        # 國道三號
        (45, 50): "樹林段",
        (50, 56): "三鶯段",
        (56, 65): "大溪段",
        (65, 70): "龍潭段",
        (70, 79): "關西段",
        (79, 85): "竹林段",
        (85, 96): "寶山段",
        (96, 103): "新竹系統段",
    }
    
    return location_mapping

def get_friendly_location(highway: str, mileage: float):
    """根據國道和里程數獲取友善地名"""
    location_mapping = create_mileage_to_location_mapping()
    
    for (start, end), location in location_mapping.items():
        if start <= mileage < end:
            return f"{highway}{location}"
    
    # 如果沒有匹配，返回里程描述
    return f"{highway} {mileage}公里處"

def fix_enhanced_data():
    """修復增強資料中的地名映射"""
    enhanced_file = "/Users/tommy/Desktop/Highway_trafficwave/train_model/configs/processed_data/enhanced_highway_data.json"
    
    print("🔧 開始修復地名映射...")
    
    # 載入增強資料
    with open(enhanced_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"載入了 {len(data)} 個文檔")
    
    # 修復每個文檔的友善位置和文本
    fixed_count = 0
    location_stats = {}
    
    for item in data:
        highway = item.get('highway', '')
        mileage = item.get('mileage', 0)
        
        if highway and mileage > 0:
            # 生成新的友善位置
            new_location = get_friendly_location(highway, mileage)
            old_location = item.get('friendly_location', '')
            
            # 更新友善位置
            item['friendly_location'] = new_location
            
            # 確保文本中包含友善位置
            if new_location not in item['text']:
                # 在文本開頭添加友善位置
                item['text'] = f"位置：{new_location}\\n{item['text']}"
                fixed_count += 1
            
            # 統計位置分布
            location_stats[new_location] = location_stats.get(new_location, 0) + 1
    
    print(f"修復了 {fixed_count} 個文檔的文本")
    print(f"\\n位置分布統計（前10個）:")
    sorted_locations = sorted(location_stats.items(), key=lambda x: x[1], reverse=True)
    for location, count in sorted_locations[:10]:
        print(f"  {location}: {count} 個文檔")
    
    # 保存修復後的資料
    backup_file = enhanced_file.replace('.json', '_backup.json')
    print(f"\\n備份原始檔案到: {backup_file}")
    
    # 先備份
    import shutil
    shutil.copy2(enhanced_file, backup_file)
    
    # 保存修復後的資料
    with open(enhanced_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"修復完成！保存到: {enhanced_file}")
    
    # 測試修復結果
    print("\\n🧪 測試修復結果...")
    wugu_docs = [item for item in data if '五股' in item['text'] or '五股' in item.get('friendly_location', '')]
    linkou_docs = [item for item in data if '林口' in item['text'] or '林口' in item.get('friendly_location', '')]
    
    print(f"包含「五股」的文檔數量: {len(wugu_docs)}")
    print(f"包含「林口」的文檔數量: {len(linkou_docs)}")
    
    if wugu_docs:
        print(f"\\n五股文檔範例:")
        print(f"  友善位置: {wugu_docs[0].get('friendly_location', 'N/A')}")
        print(f"  文本預覽: {wugu_docs[0]['text'][:200]}...")
    
    if linkou_docs:
        print(f"\\n林口文檔範例:")
        print(f"  友善位置: {linkou_docs[0].get('friendly_location', 'N/A')}")
        print(f"  文本預覽: {linkou_docs[0]['text'][:200]}...")
    
    return len(wugu_docs), len(linkou_docs)

if __name__ == "__main__":
    try:
        wugu_count, linkou_count = fix_enhanced_data()
        
        if linkou_count > 0:
            print("\\n✅ 修復成功！現在需要重新建立向量索引：")
            print("python scripts/train_rag.py --mode train --force-rebuild")
        else:
            print("\\n⚠️ 修復後仍沒有林口文檔，需要檢查里程範圍映射")
            
    except Exception as e:
        print(f"❌ 修復失敗: {e}")
        import traceback
        traceback.print_exc()