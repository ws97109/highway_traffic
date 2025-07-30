# -- coding: utf-8 --
"""
重新生成距離矩陣 (dis.csv) 的工具程式
根據實際站點連接關係建立完整的距離矩陣

流程:
1. 讀取站點連接關係
2. 建立圖結構  
3. 對每個站點執行 Dijkstra 演算法
4. 收集所有最短距離到矩陣中
5. 應用指數歸一化
6. 儲存為 CSV 檔案
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
        if vertex in seen:
            continue
        seen.add(vertex)
        
        if vertex not in graph:
            continue
            
        nodes = graph[vertex].keys()
        for w in nodes:
            if w not in seen:
                if dist + graph[vertex][w] < distance[w]:
                    heapq.heappush(pqueue, (dist + graph[vertex][w], w))
                    parent[w] = vertex
                    distance[w] = dist + graph[vertex][w]
    return parent, distance

def distance_normalization(A):
    """距離的指數歸一化"""
    # 將無窮大值替換為一個大數值，以便計算統計量
    finite_distances = A[~np.isinf(A)].flatten()
    finite_distances = finite_distances[finite_distances > 0]  # 排除 0 值
    
    if len(finite_distances) == 0:
        print("警告: 沒有有限的正距離值")
        return A
    
    std = finite_distances.std()   # 計算距離的標準差
    if std == 0:
        print("警告: 距離標準差為 0")
        return A
    
    # 應用指數歸一化
    A_normalized = np.exp(-np.square(A / std))
    
    # 將原來是無窮大的位置設為 0
    A_normalized[np.isinf(A)] = 0
    
    return A_normalized

def generate_distance_matrix(site_num=61, output_dir='../../data/Taiwan/'):
    """
    生成距離矩陣 CSV 文件
    
    Args:
        site_num: 站點數量 (默認 61)
        output_dir: 輸出目錄路徑
    """
    print(f"開始生成 {site_num} 個站點的距離矩陣...")
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 讀取站點連接關係
    adj_file_path = os.path.join(output_dir, 'adjacent_fully.csv')
    etag_file_path = os.path.join(output_dir, 'Etag.csv')
    
    # 讀取站點信息
    stations = []
    if os.path.exists(etag_file_path):
        try:
            etag_data = pd.read_csv(etag_file_path)
            print(f"讀取到站點文件: {etag_file_path}")
            print(f"站點文件形狀: {etag_data.shape}")
            
            # 使用 ID 作為站點標識
            if 'ID' in etag_data.columns:
                stations = [f"station_{int(id_val)}" for id_val in etag_data['ID'].values[:site_num]]
            else:
                stations = [f"station_{i+1}" for i in range(site_num)]
                
        except Exception as e:
            print(f"讀取站點文件時發生錯誤: {e}")
            stations = [f"station_{i+1}" for i in range(site_num)]
    else:
        print(f"未找到站點文件，使用默認命名")
        stations = [f"station_{i+1}" for i in range(site_num)]
    
    print(f"站點列表前 5 個: {stations[:5]}")
    
    # 2. 建立圖結構
    graph_dict = {station: {} for station in stations}
    
    # 讀取鄰接關係
    if os.path.exists(adj_file_path):
        try:
            adj_data = pd.read_csv(adj_file_path)
            print(f"讀取到鄰接文件: {adj_file_path}")
            print(f"鄰接文件形狀: {adj_data.shape}")
            print("鄰接關係前幾行:")
            print(adj_data.head())
            
            # 根據鄰接關係建立圖
            connection_count = 0
            for _, row in adj_data.iterrows():
                if 'src_FID' in row and 'nbr_FID' in row:
                    src_idx = int(row['src_FID']) - 1  # 轉換為 0-based index
                    nbr_idx = int(row['nbr_FID']) - 1
                    
                    if 0 <= src_idx < site_num and 0 <= nbr_idx < site_num:
                        src_station = stations[src_idx]
                        nbr_station = stations[nbr_idx]
                        
                        # 設定距離權重 (這裡使用單位距離，你可以根據實際情況調整)
                        distance_weight = 1.0
                        graph_dict[src_station][nbr_station] = distance_weight
                        graph_dict[nbr_station][src_station] = distance_weight  # 雙向連接
                        connection_count += 1
            
            print(f"建立了 {connection_count} 個連接")
            
        except Exception as e:
            print(f"讀取鄰接文件時發生錯誤: {e}")
            # 使用線性連接作為備選方案
            print("使用線性連接作為備選方案...")
            for i in range(site_num - 1):
                current_station = stations[i]
                next_station = stations[i + 1]
                graph_dict[current_station][next_station] = 1.0
                graph_dict[next_station][current_station] = 1.0
    else:
        print("未找到鄰接文件，使用線性連接...")
        for i in range(site_num - 1):
            current_station = stations[i]
            next_station = stations[i + 1]
            graph_dict[current_station][next_station] = 1.0
            graph_dict[next_station][current_station] = 1.0
    
    # 3. 對每個站點執行 Dijkstra 演算法 & 4. 收集所有最短距離到矩陣中
    print("開始計算最短距離矩陣...")
    distance_matrix = np.full((site_num, site_num), math.inf)
    
    for i, station_i in enumerate(stations):
        if i % 10 == 0:
            print(f"處理站點 {i+1}/{site_num}: {station_i}")
            
        parent_dict, distance_dict = dijkstra(graph_dict, station_i)
        
        for j, station_j in enumerate(stations):
            if station_j in distance_dict:
                distance_matrix[i][j] = distance_dict[station_j]
            else:
                distance_matrix[i][j] = math.inf
    
    print("距離計算完成，開始應用歸一化...")
    
    # 5. 應用指數歸一化
    normalized_matrix = distance_normalization(distance_matrix)
    
    # 6. 儲存為 CSV 檔案
    output_file = os.path.join(output_dir, 'dis_new.csv')
    
    # 保存到 CSV
    df = pd.DataFrame(normalized_matrix)
    df.to_csv(output_file, header=False, index=False)
    
    print(f"距離矩陣已保存至: {output_file}")
    
    # 驗證生成的文件
    try:
        verification_data = pd.read_csv(output_file, header=None)
        print(f"驗證 - 新生成的檔案形狀: {verification_data.shape}")
        
        if verification_data.shape == (site_num, site_num):
            print("✅ dis_new.csv 生成成功，尺寸正確！")
            
            # 備份原文件並替換
            original_file = os.path.join(output_dir, 'dis.csv')
            if os.path.exists(original_file):
                backup_file = os.path.join(output_dir, 'dis_backup.csv')
                shutil.copy2(original_file, backup_file)
                print(f"已備份原文件至: {backup_file}")
            
            shutil.move(output_file, original_file)
            print(f"✅ 已將新文件移動至: {original_file}")
            
            # 顯示統計信息
            print(f"\n距離矩陣統計信息:")
            print(f"形狀: {verification_data.shape}")
            print(f"數值範圍: {verification_data.values.min():.6f} 到 {verification_data.values.max():.6f}")
            print(f"對角線值範圍: {np.diag(verification_data.values).min():.6f} 到 {np.diag(verification_data.values).max():.6f}")
            
            return True
        else:
            print(f"❌ 尺寸不正確，預期 ({site_num}, {site_num})，實際 {verification_data.shape}")
            return False
            
    except Exception as e:
        print(f"驗證時發生錯誤: {e}")
        return False

if __name__ == '__main__':
    # 設定參數
    SITE_NUM = 61  # 根據 Etag.csv 的站點數
    
    # 執行生成
    success = generate_distance_matrix(site_num=SITE_NUM)
    
    if success:
        print("\n🎉 距離矩陣生成成功！")
        print("現在可以重新運行 MT-STNet 訓練程式了。")
    else:
        print("\n❌ 生成過程中出現問題，請檢查錯誤訊息。")
