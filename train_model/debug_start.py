#!/usr/bin/env python3
"""
RAG 系統調試啟動腳本
用於診斷和解決啟動問題
"""

import os
import sys
import traceback
from pathlib import Path

# 設定當前目錄
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
print(f"當前工作目錄: {current_dir}")
print(f"Python 路徑: {sys.path[:3]}...")

def test_basic_imports():
    """測試基本模組導入"""
    print("\\n=== 測試基本模組導入 ===")
    
    # 測試標準庫
    try:
        import json, yaml, asyncio
        print("✓ 標準庫模組導入成功")
    except ImportError as e:
        print(f"✗ 標準庫模組導入失敗: {e}")
        return False
    
    # 測試第三方庫
    try:
        import httpx, pandas, numpy
        print("✓ 第三方庫模組導入成功")
    except ImportError as e:
        print(f"✗ 第三方庫模組導入失敗: {e}")
        print("請執行: pip install httpx pandas numpy")
        return False
    
    # 測試 AI 相關庫
    try:
        import sentence_transformers, chromadb
        print("✓ AI 相關庫模組導入成功")
    except ImportError as e:
        print(f"✗ AI 相關庫模組導入失敗: {e}")
        print("請執行: pip install sentence-transformers chromadb")
        return False
    
    return True

def test_custom_modules():
    """測試自定義模組"""
    print("\\n=== 測試自定義模組導入 ===")
    
    # 測試配置管理器
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        print(f"✓ 配置管理器導入成功: {config_manager.config_path}")
    except Exception as e:
        print(f"✗ 配置管理器導入失敗: {e}")
        traceback.print_exc()
        return False
    
    # 測試 CSV 處理器
    try:
        from data_processing.csv_processor import HighwayCSVProcessor
        processor = HighwayCSVProcessor()
        print("✓ CSV 處理器導入成功")
    except Exception as e:
        print(f"✗ CSV 處理器導入失敗: {e}")
        traceback.print_exc()
        return False
    
    # 測試向量存儲
    try:
        from embeddings.vector_store import VectorStore
        print("✓ 向量存儲模組導入成功")
    except Exception as e:
        print(f"✗ 向量存儲模組導入失敗: {e}")
        traceback.print_exc()
        return False
    
    # 測試 Ollama 客戶端
    try:
        from models.ollama_client import OllamaClient
        print("✓ Ollama 客戶端模組導入成功")
    except Exception as e:
        print(f"✗ Ollama 客戶端模組導入失敗: {e}")
        traceback.print_exc()
        return False
    
    return True

async def test_ollama_connection():
    """測試 Ollama 連接"""
    print("\\n=== 測試 Ollama 連接 ===")
    
    try:
        from models.ollama_client import OllamaClient
        client = OllamaClient()
        
        is_connected = await client.check_connection()
        if is_connected:
            print("✓ Ollama 服務連接成功")
            return True
        else:
            print("✗ Ollama 服務連接失敗")
            print("請確保:")
            print("1. Ollama 服務正在運行: ollama serve")
            print("2. 已安裝模型: ollama pull deepseek-r1:32b")
            return False
            
    except Exception as e:
        print(f"✗ 測試 Ollama 連接時出錯: {e}")
        traceback.print_exc()
        return False

def test_data_files():
    """測試資料文件"""
    print("\\n=== 測試資料文件 ===")
    
    data_dir = current_dir.parent / "data" / "Taiwan"
    print(f"資料目錄: {data_dir}")
    
    if not data_dir.exists():
        print(f"✗ 資料目錄不存在: {data_dir}")
        return False
    
    required_files = [
        "國道一號_整合資料.csv",
        "國道三號_整合資料.csv"
    ]
    
    all_exist = True
    for file_name in required_files:
        file_path = data_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✓ {file_name}: {size:,} bytes")
        else:
            print(f"✗ 缺少文件: {file_name}")
            all_exist = False
    
    return all_exist

async def test_rag_components():
    """測試 RAG 組件"""
    print("\\n=== 測試 RAG 組件整合 ===")
    
    try:
        # 初始化各組件
        from data_processing.csv_processor import HighwayCSVProcessor
        from embeddings.vector_store import VectorStore
        from models.ollama_client import OllamaClient
        
        print("正在初始化組件...")
        
        # CSV 處理器
        csv_processor = HighwayCSVProcessor()
        print("✓ CSV 處理器初始化")
        
        # 向量存儲
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        print(f"✓ 向量存儲初始化: {stats.get('document_count', 0)} 個文檔")
        
        # Ollama 客戶端
        ollama_client = OllamaClient()
        connection_ok = await ollama_client.check_connection()
        print(f"{'✓' if connection_ok else '✗'} Ollama 客戶端: {'已連接' if connection_ok else '未連接'}")
        
        return True
        
    except Exception as e:
        print(f"✗ RAG 組件測試失敗: {e}")
        traceback.print_exc()
        return False

def show_next_steps(all_passed):
    """顯示下一步建議"""
    print("\\n" + "="*60)
    
    if all_passed:
        print("🎉 所有測試通過！系統準備就緒")
        print("\\n下一步:")
        print("1. 訓練系統: python scripts/train_rag.py --mode train")
        print("2. 開始聊天: python scripts/train_rag.py --mode chat")
        print("3. 或使用: python quick_start.py")
    else:
        print("❌ 部分測試失敗，請根據上述錯誤信息修復問題")
        print("\\n常見解決方案:")
        print("1. 安裝缺少的依賴: pip install -r requirements.txt")
        print("2. 啟動 Ollama 服務: ollama serve")
        print("3. 下載模型: ollama pull deepseek-r1:32b")
        print("4. 檢查資料文件是否存在於 ../data/Taiwan/ 目錄")
    
    print("\\n如需幫助，請查看: RAG_啟用指南.md")
    print("="*60)

async def main():
    """主函數"""
    print("🔍 RAG 系統調試診斷工具")
    print("="*60)
    
    # 執行各項測試
    tests_results = []
    
    # 1. 基本模組導入測試
    tests_results.append(test_basic_imports())
    
    # 2. 自定義模組測試
    tests_results.append(test_custom_modules())
    
    # 3. Ollama 連接測試
    tests_results.append(await test_ollama_connection())
    
    # 4. 資料文件測試
    tests_results.append(test_data_files())
    
    # 5. RAG 組件整合測試
    tests_results.append(await test_rag_components())
    
    # 顯示結果和建議
    all_passed = all(tests_results)
    show_next_steps(all_passed)
    
    return all_passed

if __name__ == "__main__":
    try:
        import asyncio
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\\n程序被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\\n程序執行失敗: {e}")
        traceback.print_exc()
        sys.exit(1)