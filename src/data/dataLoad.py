import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_traffic_data(file_path=None):
    """載入交通資料"""
    if file_path is None:
        file_path = '../data/Taiwan/train_enhanced_full.csv'
    return pd.read_csv(file_path)

def analyze_traffic_data(df):
    """分析交通資料"""
    print("=== 資料基本資訊 ===")
    print(f"資料形狀: {df.shape}")
    print(f"欄位: {list(df.columns)}")
    print(f"資料類型:\n{df.dtypes}")

    print("\n=== 前10筆資料 ===")
    print(df.head(10))

    print("\n=== 基本統計 ===")
    print(df.describe())

    print("\n=== 缺失值檢查 ===")
    missing_data = df.isnull().sum()
    print(missing_data[missing_data > 0])

    print("\n=== 時間範圍分析 ===")
    print(f"日期範圍: {df['date'].min()} 到 {df['date'].max()}")
    print(f"總天數: {df['date'].nunique()}")
    print(f"小時範圍: {df['hour'].min()} 到 {df['hour'].max()}")

    print("\n=== 站點資訊 ===")
    print(f"總站點數: {df['station'].nunique()}")
    print(f"站點列表: {sorted(df['station'].unique())}")

    print("\n=== 交通指標概況 ===")
    print(f"車流量範圍: {df['flow'].min():.2f} - {df['flow'].max():.2f}")
    print(f"平均速度範圍: {df['median_speed'].min():.2f} - {df['median_speed'].max():.2f}")
    print(f"旅行時間範圍: {df['avg_travel_time'].min():.2f} - {df['avg_travel_time'].max():.2f}")

def create_visualizations(df):
    """創建視覺化圖表"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    axes[0,0].hist(df['flow'], bins=50, alpha=0.7, color='skyblue')
    axes[0,0].set_title('車流量分布')
    axes[0,0].set_xlabel('車流量 (車/小時)')
    axes[0,0].set_ylabel('頻率')
    
    axes[0,1].hist(df['median_speed'], bins=50, alpha=0.7, color='lightgreen')
    axes[0,1].set_title('速度分布')
    axes[0,1].set_xlabel('中位數速度 (km/h)')
    axes[0,1].set_ylabel('頻率')
    
    hour_counts = df['hour'].value_counts().sort_index()
    axes[1,0].plot(hour_counts.index, hour_counts.values, marker='o')
    axes[1,0].set_title('各小時資料筆數')
    axes[1,0].set_xlabel('小時')
    axes[1,0].set_ylabel('資料筆數')
    axes[1,0].grid(True)
    
    station_counts = df['station'].value_counts()
    axes[1,1].bar(range(len(station_counts)), station_counts.values)
    axes[1,1].set_title('各站點資料筆數')
    axes[1,1].set_xlabel('站點（按資料量排序）')
    axes[1,1].set_ylabel('資料筆數')
    
    plt.tight_layout()
    plt.show()

def check_time_continuity(df):
    """檢查時間連續性"""
    print("\n=== 時間連續性檢查 ===")
    
    unique_stations = df['station'].unique()[:10]  # 檢查前10個站點
    
    for station in unique_stations:
        station_data = df[df['station'] == station].copy()
        station_data['datetime'] = pd.to_datetime(
            station_data['date'] + ' ' + 
            station_data['hour'].astype(str).str.zfill(2) + ':' +
            (station_data['minute'] // 5 * 5).astype(str).str.zfill(2)
        )
        station_data = station_data.sort_values('datetime')
        
        print(f"\n站點 {station}:")
        print(f"  資料筆數: {len(station_data)}")
        print(f"  日期範圍: {station_data['date'].min()} - {station_data['date'].max()}")
        
        date_range = pd.date_range(
            start=station_data['datetime'].min().date(),
            end=station_data['datetime'].max().date(),
            freq='D'
        )
        expected_points = len(date_range) * 24 * 12
        completion_rate = len(station_data) / expected_points * 100
        print(f"  資料完整度: {completion_rate:.1f}%")

if __name__ == "__main__":
    # 載入和分析資料
    df = load_traffic_data()
    analyze_traffic_data(df)
    create_visualizations(df)
    check_time_continuity(df)
    
    print("\n=== 第一步完成 ===")
    print("資料載入成功，基本探索完成！")
    print("接下來我們將進行震波檢測。")
