# -- coding: utf-8 --
"""
生成最短路徑矩陣 (sp.csv) 的工具程式
用於為 MT-STNet 模型生成適合的最短路徑數據
"""
import heapq
import math
import numpy as np
import pandas as pd
import csv
import os
import shutil

def init_distance(graph, s):
    """初始化距離字典"""
    distance = {s: 0}
    for vertex in graph:
        if vertex != s:
            distance[vertex] = math.inf
    return distance

def dijkstra(graph, s):
    """使用 Dijkstra 演算法計算最短路徑"""
    pqueue = []
    heapq.heappush(pqueue, (0, s))
    seen = set()
    parent = {s: None}
    distance = init_distance(graph, s)

    while len(pqueue) > 0:
        pair = heapq.heappop(pqueue)
        dist = pair[0]
        vertex = pair[1]
        seen.add(vertex)
        nodes = graph[vertex].keys()
        for w in nodes:
            if w not in seen:
                if dist + graph[vertex][w] < distance[w]:
                    heapq.heappush(pqueue, (dist + graph[vertex][w], w))
                    parent[w] = vertex
                    distance[w] = dist + graph[vertex][w]
    return parent, distance

def distance_path(graph, s, end):
    """計算兩點間的最短路徑"""
    parent, distance = dijkstra(graph, s)
    if distance[end] == math.inf:
        return []  # 無法到達
    
    path = [end]
    while parent[end] is not None:
        path.append(parent[end])
        end = parent[end]
    path.reverse()
    return path

def generate_sp_csv(site_num=61, roads_num=108, output_dir='../../data/Taiwan/'):
    """
    生成最短路徑矩陣 CSV 文件
    
    Args:
        site_num: 站點數量 (默認 61)
        roads_num: 道路/邊的數量 (默認 108)
        output_dir: 輸出目錄路徑
    """
    print(f"開始生成 {site_num} 個站點的最短路徑矩陣...")
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 檢查是否有現有的鄰接關係文件
    adj_file_path = os.path.join(output_dir, 'adjacent_fully.csv')
    try:
        if os.path.exists(adj_file_path):
            adj_data = pd.read_csv(adj_file_path)
            print(f"讀取到鄰接文件: {adj_file_path}")
            print(f"鄰接文件形狀: {adj_data.shape}")
            print("鄰接文件前幾行:")
            print(adj_data.head())
        else:
            print(f"未找到鄰接文件: {adj_file_path}")
            adj_data = None
    except Exception as e:
        print(f"讀取鄰接文件時發生錯誤: {e}")
        adj_data = None
        
    # 創建站點列表
    stations = [f"station_{i}" for i in range(site_num)]
    
    # 創建基本的圖結構
    graph_dict = {station_i: {} for station_i in stations}
    
    # 如果有鄰接數據，則使用它；否則創建線性連接
    if adj_data is not None and len(adj_data) > 0:
        # 使用實際的鄰接關係
        for _, row in adj_data.iterrows():
            if 'src_FID' in row and 'nbr_FID' in row:
                src_idx = int(row['src_FID']) - 1  # 轉換為 0-based index
                nbr_idx = int(row['nbr_FID']) - 1
                if 0 <= src_idx < site_num and 0 <= nbr_idx < site_num:
                    src_station = stations[src_idx]
                    nbr_station = stations[nbr_idx]
                    graph_dict[src_station][nbr_station] = 1.0
                    graph_dict[nbr_station][src_station] = 1.0  # 雙向連接
    else:
        # 創建線性連接作為備選方案
        print("使用線性連接作為備選方案...")
        for i in range(site_num):
            current_station = stations[i]
            # 與前一個站點相連
            if i > 0:
                prev_station = stations[i-1]
                graph_dict[current_station][prev_station] = 1.0
                graph_dict[prev_station][current_station] = 1.0
            
            # 與後一個站點相連
            if i < site_num - 1:
                next_station = stations[i+1]
                graph_dict[current_station][next_station] = 1.0
                graph_dict[next_station][current_station] = 1.0
    
    # 對於沒有直接連接的站點，設為無窮大
    for station_i in stations:
        for station_j in stations:
            if station_j not in graph_dict[station_i]:
                if station_i != station_j:
                    graph_dict[station_i][station_j] = math.inf
                else:
                    graph_dict[station_i][station_j] = 0
    
    print(f"開始生成 {site_num}×{site_num} = {site_num*site_num} 行的 sp.csv")
    
    # 生成 sp.csv
    output_file = os.path.join(output_dir, 'sp_new.csv')
    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        
        # 為每個起點站點計算到所有其他站點的最短路徑
        row_count = 0
        for i, station_i in enumerate(stations):
            parent_dict, distance_dict = dijkstra(graph_dict, station_i)
            
            for j, station_j in enumerate(stations):
                if distance_dict[station_j] < 200:  # 如果距離合理
                    sp = distance_path(graph_dict, station_i, station_j)
                    if len(sp) > 1:
                        # 創建路徑編碼
                        path_length = len(sp) - 1
                        left_sp = [min(path_length, roads_num-1) for _ in range(min(path_length, 15))]
                    else:
                        left_sp = [0 if station_i == station_j else roads_num-1]
                else:
                    left_sp = [roads_num-1]  # 無法到達時使用最大值
                
                # 補齊到 15 列
                while len(left_sp) < 15:
                    left_sp.append(roads_num-1)
                
                writer.writerow(left_sp[:15])  # 確保只有 15 列
                row_count += 1
                
                if row_count % 1000 == 0:
                    print(f"已處理 {row_count}/{site_num*site_num} 行 ({row_count/(site_num*site_num)*100:.1f}%)")
    
    print(f"sp.csv 生成完成，總共 {row_count} 行")
    print(f"預期行數: {site_num} × {site_num} = {site_num**2}")
    
    # 驗證生成的文件
    try:
        new_sp = pd.read_csv(output_file, header=None)
        print(f"新生成的檔案形狀: {new_sp.shape}")
        if new_sp.shape[0] == site_num * site_num and new_sp.shape[1] == 15:
            print("✅ sp_new.csv 生成成功，尺寸正確！")
            # 替換原文件
            original_file = os.path.join(output_dir, 'sp.csv')
            if os.path.exists(original_file):
                # 備份原文件
                backup_file = os.path.join(output_dir, 'sp_backup.csv')
                shutil.copy2(original_file, backup_file)
                print(f"已備份原文件至: {backup_file}")
            
            shutil.move(output_file, original_file)
            print(f"✅ 已將新文件移動至: {original_file}")
            return True
        else:
            print(f"❌ 尺寸不正確，預期 ({site_num**2}, 15)，實際 {new_sp.shape}")
            return False
    except Exception as e:
        print(f"驗證時發生錯誤: {e}")
        return False

if __name__ == '__main__':
    # 設定參數
    SITE_NUM = 61  # 根據 Etag.csv 的站點數
    ROADS_NUM = 108  # 邊的數量
    
    # 執行生成
    success = generate_sp_csv(site_num=SITE_NUM, roads_num=ROADS_NUM)
    
    if success:
        print("\n🎉 最短路徑矩陣生成成功！")
        print("現在可以重新運行 MT-STNet 訓練程式了。")
    else:
        print("\n❌ 生成過程中出現問題，請檢查錯誤訊息。")
