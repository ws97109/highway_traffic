#!/usr/bin/env python3
"""
整合版 RAG 系統快速啟動腳本
包含完整的系統檢查、訓練，以及網頁服務器啟動功能
"""

import os
import sys
import asyncio
import subprocess
import platform
import shutil
from pathlib import Path
from loguru import logger
import importlib

# 設定路徑
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 配置日誌
logger.add("quick_start.log", rotation="10 MB", level="INFO")

def check_ollama_installation():
    """檢查 Ollama 是否已安裝"""
    return shutil.which("ollama") is not None

def check_ollama_service():
    """檢查 Ollama 服務狀態和可用模型"""
    try:
        import httpx
        
        # 檢查服務
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            return True, models
        else:
            return False, []
    except Exception:
        return False, []

def download_recommended_model():
    """下載推薦的模型"""
    recommended_models = ['deepseek-r1:32b', 'llama3.1:8b', 'llama3:latest']
    
    for model in recommended_models:
        logger.info(f"嘗試下載模型: {model}")
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                logger.info(f"✓ 成功下載模型: {model}")
                return model
            else:
                logger.warning(f"下載 {model} 失敗: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning(f"下載 {model} 超時")
        except Exception as e:
            logger.warning(f"下載 {model} 出錯: {e}")
    
    logger.error("無法下載任何推薦模型")
    return None

def install_python_dependencies():
    """安裝 Python 依賴"""
    requirements_file = current_dir / "requirements.txt"
    
    if not requirements_file.exists():
        logger.warning("未找到 requirements.txt 文件")
        return True
    
    try:
        logger.info("安裝 Python 依賴...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✓ Python 依賴安裝完成")
            return True
        else:
            logger.error(f"Python 依賴安裝失敗: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"安裝依賴時發生錯誤: {e}")
        return False

def check_data_files():
    """檢查必要的資料文件"""
    data_dir = current_dir.parent / "data" / "Taiwan"
    
    if not data_dir.exists():
        logger.error(f"資料目錄不存在: {data_dir}")
        return False
    
    required_files = [
        "國道一號_整合資料.csv",
        "國道三號_整合資料.csv",
        "geometric_statistical_N01.json",
        "geometric_statistical_N03.json"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = data_dir / file_name
        if file_path.exists():
            logger.info(f"✓ 找到資料文件: {file_name}")
        else:
            missing_files.append(file_name)
            logger.error(f"✗ 缺少資料文件: {file_name}")
    
    if missing_files:
        logger.error("請確保以下資料文件存在於 data/Taiwan/ 目錄中：")
        for file_name in missing_files:
            logger.error(f"  - {file_name}")
        return False
    
    return True

async def run_rag_training():
    """執行 RAG 訓練"""
    logger.info("開始執行 RAG 系統訓練...")
    
    try:
        from scripts.train_rag import RAGTrainer
        trainer = RAGTrainer()
        await trainer.run_training_pipeline()
        logger.info("✓ RAG 系統訓練完成")
        return True
    except Exception as e:
        logger.error(f"✗ RAG 系統訓練失敗: {e}")
        return False

async def test_rag_system():
    """測試 RAG 系統"""
    logger.info("開始測試 RAG 系統...")
    
    try:
        from scripts.train_rag import RAGTrainer
        trainer = RAGTrainer()
        await trainer.setup_components()
        await trainer.test_rag_system()
        logger.info("✓ RAG 系統測試完成")
        return True
    except Exception as e:
        logger.error(f"✗ RAG 系統測試失敗: {e}")
        return False

def print_usage_instructions():
    """打印使用說明"""
    print("\n" + "="*60)
    print("🚗 高速公路 RAG 系統啟動完成！")
    print("="*60)
    print("\n可用命令：")
    print("1. 啟動互動聊天：")
    print("   python scripts/train_rag.py --mode chat")
    print("\n2. 重新訓練系統：")
    print("   python scripts/train_rag.py --mode train --force-rebuild")
    print("\n3. 僅測試系統：")
    print("   python scripts/train_rag.py --mode test")
    print("\n示例問題：")
    print("- 國道一號的車道寬度通常是多少？")
    print("- 國道三號和國道一號在路面設計上有什麼不同？")
    print("- 高速公路的縱向坡度一般是多少？")
    print("\n" + "="*60)

async def start_web_server():
    """啟動 FastAPI 網頁服務器"""
    logger.info("準備啟動 FastAPI 網頁服務器...")
    
    try:
        # 檢查 main.py 是否存在
        main_py = current_dir / "main.py"
        if not main_py.exists():
            logger.error("未找到 main.py 檔案")
            return False
        
        # 動態導入 main 模組
        logger.info("正在啟動 FastAPI 服務器...")
        logger.info("服務器將在 http://localhost:8000 啟動")
        logger.info("API 文檔可在 http://localhost:8000/docs 查看")
        logger.info("按 Ctrl+C 停止服務器")
        
        # 執行 main.py
        result = subprocess.run([sys.executable, str(main_py)], cwd=str(current_dir))
        
        if result.returncode == 0:
            logger.info("✓ 網頁服務器正常關閉")
            return True
        else:
            logger.error("✗ 網頁服務器異常退出")
            return False
            
    except KeyboardInterrupt:
        logger.info("用戶中斷服務器")
        return True
    except Exception as e:
        logger.error(f"啟動網頁服務器失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def start_interactive_chat():
    """啟動互動聊天"""
    logger.info("啟動互動聊天...")
    try:
        import importlib
        train_rag_module = importlib.import_module('scripts.train_rag')
        RAGTrainer = train_rag_module.RAGTrainer
        
        trainer = RAGTrainer()
        await trainer.setup_components()
        await trainer.interactive_chat()
        return True
    except KeyboardInterrupt:
        logger.info("用戶退出聊天")
        return True
    except Exception as e:
        logger.error(f"啟動聊天模式失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def show_operation_menu():
    """顯示操作選單"""
    print("\n" + "="*60)
    print("🚀 系統準備就緒！請選擇操作模式：")
    print("="*60)
    print("1. 啟動網頁服務器 (推薦)")
    print("   - 提供完整的 Web API 服務")
    print("   - 包含 RAG 聊天和交通管理顧問")
    print("   - 可通過瀏覽器訪問")
    print()
    print("2. 啟動命令行聊天")
    print("   - 直接在終端中對話")
    print("   - 適合快速測試")
    print()
    print("3. 重新訓練系統")
    print("   - 重新處理資料並訓練")
    print("   - 適合更新資料後使用")
    print()
    print("4. 退出")
    print("="*60)

async def main():
    """主函數"""
    print("🚀 RAG 系統整合啟動腳本")
    print("="*50)
    
    # 1. 檢查 Ollama 安裝
    logger.info("步驟 1: 檢查 Ollama 安裝...")
    if not check_ollama_installation():
        logger.error("請先安裝 Ollama: https://ollama.ai")
        return
    
    # 2. 檢查 Ollama 服務
    logger.info("步驟 2: 檢查 Ollama 服務...")
    service_running, models = check_ollama_service()
    if not service_running:
        logger.error("請啟動 Ollama 服務: ollama serve")
        return
    
    # 3. 檢查並下載模型
    if not models:
        logger.info("步驟 3: 下載推薦模型...")
        model = download_recommended_model()
        if not model:
            return
    else:
        logger.info("✓ 已有可用模型")
    
    # 4. 安裝 Python 依賴
    logger.info("步驟 4: 檢查 Python 依賴...")
    if not install_python_dependencies():
        return
    
    # 5. 檢查資料文件
    logger.info("步驟 5: 檢查資料文件...")
    if not check_data_files():
        return
    
    # 6. 訓練 RAG 系統
    logger.info("步驟 6: 訓練 RAG 系統...")
    if not await run_rag_training():
        logger.warning("訓練失敗，嘗試僅測試系統...")
        if not await test_rag_system():
            logger.error("系統測試也失敗，請檢查配置")
            return
    
    # 7. 顯示使用說明
    print_usage_instructions()
    
    # 8. 顯示操作選單並處理用戶選擇
    while True:
        try:
            show_operation_menu()
            choice = input("\n請輸入選擇 (1-4): ").strip()
            
            if choice == "1":
                logger.info("用戶選擇：啟動網頁服務器")
                success = await start_web_server()
                if success:
                    print("\n網頁服務器已關閉，返回選單...")
                    continue
                else:
                    print("\n網頁服務器啟動失敗，請檢查錯誤信息")
                    
            elif choice == "2":
                logger.info("用戶選擇：啟動命令行聊天")
                success = await start_interactive_chat()
                if success:
                    print("\n聊天會話已結束，返回選單...")
                    continue
                    
            elif choice == "3":
                logger.info("用戶選擇：重新訓練系統")
                success = await run_rag_training()
                if success:
                    print("\n✓ 重新訓練完成！")
                else:
                    print("\n✗ 重新訓練失敗，請檢查錯誤信息")
                continue
                
            elif choice == "4":
                logger.info("用戶選擇：退出")
                print("再見！")
                break
                
            else:
                print("無效選擇，請輸入 1-4")
                continue
                
        except KeyboardInterrupt:
            print("\n\n用戶中斷程序，再見！")
            break
        except Exception as e:
            logger.error(f"操作失敗: {e}")
            print(f"操作失敗: {e}")
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用戶中斷")
    except Exception as e:
        logger.error(f"程序執行失敗: {e}")
        print(f"\n程序執行失敗: {e}")
        import traceback
        traceback.print_exc()