#!/usr/bin/env python3
"""測試測站匹配功能"""

import pandas as pd
import os

def load_station_data():
    """載入測站資料"""
    try:
        csv_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'Taiwan', 'Etag.csv')
        print(f"讀取測站資料: {csv_file}")
        
        df = pd.read_csv(csv_file)
        print(f"總共載入 {len(df)} 個測站")
        
        stations = []
        for _, row in df.iterrows():
            station_id = str(row['編號']).strip()
            name = f"{row['交流道(起)']}-{row['交流道(迄)']}"  # 組合名稱
            
            # 解析座標
            lat_str = str(row['緯度(北緯)']).replace('N', '').strip()
            lng_str = str(row['經度(東經)']).replace('E', '').strip()
            
            try:
                lat = float(lat_str)
                lng = float(lng_str)
                
                station_info = {
                    'station_id': station_id,
                    'name': name,
                    'latitude': lat,
                    'longitude': lng,
                }
                stations.append(station_info)
                
            except (ValueError, TypeError) as e:
                print(f"  跳過無效座標的測站 {station_id}: {e}")
                continue
        
        print(f"成功解析 {len(stations)} 個測站")
        return stations
        
    except Exception as e:
        print(f"載入測站資料失敗: {e}")
        return []

def find_station_info(station_id, stations_info):
    """精確匹配站點資訊"""
    print(f"\n尋找測站: {station_id}")
    
    # 直接匹配
    for info in stations_info:
        if info['station_id'] == station_id:
            print(f"  直接匹配成功: {info}")
            return info
    
    print("  直接匹配失敗，嘗試格式轉換...")
    
    # 處理格式差異：01F0928N -> 01F-092.8N
    try:
        if len(station_id) >= 8 and station_id.startswith(('01F', '03F')):
            highway = station_id[:3]  # 01F 或 03F
            km_part = station_id[3:7]  # 0928
            direction = station_id[-1]  # N 或 S
            
            print(f"  解析: highway={highway}, km_part={km_part}, direction={direction}")
            
            # 轉換為標準格式：01F-092.8N
            km_major = km_part[:3].lstrip('0') or '0'  # 092 -> 92
            km_minor = km_part[3]  # 8
            
            standard_format = f"{highway}-{km_major}.{km_minor}{direction}"
            print(f"  標準格式: {standard_format}")
            
            # 尋找匹配
            for info in stations_info:
                if info['station_id'] == standard_format:
                    print(f"  標準格式匹配成功: {info}")
                    return info
                    
            # 嘗試其他可能的格式
            alt_formats = [
                f"{highway}-0{km_major}.{km_minor}{direction}",  # 01F-092.8N
                f"{highway}-{km_major}{direction}",              # 01F-92N
                f"{highway}0{km_major}.{km_minor}{direction}",   # 01F092.8N
            ]
            
            print(f"  嘗試替代格式: {alt_formats}")
            
            for alt_format in alt_formats:
                for info in stations_info:
                    if info['station_id'] == alt_format:
                        print(f"  替代格式匹配成功: {alt_format} -> {info}")
                        return info
                        
    except Exception as e:
        print(f"  格式轉換錯誤: {e}")
    
    print(f"  找不到測站: {station_id}")
    return None

# 主測試
if __name__ == "__main__":
    # 載入測站資料
    stations = load_station_data()
    
    if stations:
        # 顯示前5個測站作為樣本
        print("\n前5個測站樣本:")
        for i, station in enumerate(stations[:5]):
            print(f"  {i+1}. {station}")
        
        # 測試具體的測站匹配
        test_stations = ['01F0928N', '01F0339S', '01F0376S', '01F0633S']
        
        print(f"\n測試匹配:")
        for test_id in test_stations:
            result = find_station_info(test_id, stations)
            if result:
                print(f"✓ {test_id} -> {result['name']} ({result['latitude']}, {result['longitude']})")
            else:
                print(f"✗ {test_id} -> 找不到")
    else:
        print("無法載入測站資料")
