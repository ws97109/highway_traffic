#!/usr/bin/env python3
"""
整合版 RAG 系統快速啟動腳本
包含完整的系統檢查、訓練，以及網頁服務器啟動功能
修復 NumPy 2.0 相容性問題
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

def check_numpy_compatibility():
    """檢查並修復 NumPy 相容性問題"""
    try:
        import numpy as np
        numpy_version = np.__version__
        logger.info(f"檢測到 NumPy 版本: {numpy_version}")
        
        # 檢查是否為 NumPy 2.0+
        if numpy_version.startswith('2.'):
            logger.warning("檢測到 NumPy 2.0+，可能存在相容性問題")
            print("⚠️  檢測到 NumPy 2.0+，建議降級以避免相容性問題")
            
            response = input("是否自動降級 NumPy 到 1.25.2？(y/n): ").lower().strip()
            if response in ['y', 'yes', '是']:
                return fix_numpy_version()
            else:
                print("跳過 NumPy 降級，可能會遇到相容性問題...")
                return True
        else:
            logger.info("✓ NumPy 版本相容")
            return True
            
    except ImportError:
        logger.warning("NumPy 未安裝，將在依賴安裝步驟中處理")
        return True
    except Exception as e:
        logger.error(f"NumPy 版本檢查失敗: {e}")
        return True  # 繼續執行，在後續步驟中處理

def fix_numpy_version():
    """修復 NumPy 版本相容性"""
    try:
        logger.info("開始修復 NumPy 版本相容性...")
        print("🔧 正在修復 NumPy 相容性問題...")
        
        # 降級 NumPy
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "numpy==1.25.2", "--force-reinstall"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"NumPy 降級失敗: {result.stderr}")
            print("❌ NumPy 降級失敗，請手動執行:")
            print("pip install numpy==1.25.2 --force-reinstall")
            return False
        
        # 重新安裝可能受影響的套件
        affected_packages = ["sentence-transformers", "chromadb"]
        for package in affected_packages:
            logger.info(f"重新安裝 {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--force-reinstall"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"{package} 重新安裝失敗，稍後會重試")
        
        logger.info("✓ NumPy 相容性修復完成")
        print("✓ NumPy 相容性修復完成")
        return True
        
    except Exception as e:
        logger.error(f"NumPy 修復過程出錯: {e}")
        print(f"❌ NumPy 修復失敗: {e}")
        return False

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
    recommended_models = ['qwen2.5:7b']
    
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
    """安裝 Python 依賴，確保 NumPy 相容性"""
    requirements_file = current_dir / "requirements.txt"
    
    if not requirements_file.exists():
        logger.warning("未找到 requirements.txt 文件")
        return True
    
    try:
        logger.info("安裝 Python 依賴...")
        print("📦 正在安裝 Python 依賴（可能需要幾分鐘）...")
        
        # 首先確保使用正確的 NumPy 版本
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "numpy==1.25.2"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning("NumPy 安裝警告，繼續安裝其他依賴...")
        
        # 安裝其他依賴
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
            print("❌ 部分依賴安裝失敗，嘗試手動修復...")
            
            # 嘗試修復常見問題
            return fix_dependency_issues()
            
    except Exception as e:
        logger.error(f"安裝依賴時發生錯誤: {e}")
        return False

def fix_dependency_issues():
    """修復常見的依賴問題"""
    try:
        logger.info("嘗試修復依賴問題...")
        print("🔧 正在嘗試修復依賴問題...")
        
        # 常見問題修復命令
        fix_commands = [
            # 確保 NumPy 版本正確
            [sys.executable, "-m", "pip", "install", "numpy==1.25.2", "--force-reinstall"],
            # 重新安裝核心 AI 套件
            [sys.executable, "-m", "pip", "install", "sentence-transformers==2.2.2", "--force-reinstall"],
            [sys.executable, "-m", "pip", "install", "chromadb==0.4.18", "--force-reinstall"],
            [sys.executable, "-m", "pip", "install", "torch==2.1.2", "--force-reinstall"],
        ]
        
        for i, cmd in enumerate(fix_commands, 1):
            print(f"   修復步驟 {i}/{len(fix_commands)}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"修復步驟 {i} 失敗，但繼續執行...")
        
        print("✓ 依賴修復嘗試完成")
        return True
        
    except Exception as e:
        logger.error(f"依賴修復失敗: {e}")
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
    """執行 RAG 訓練，包含錯誤處理"""
    logger.info("開始執行 RAG 系統訓練...")
    
    try:
        # 檢查 NumPy 版本
        import numpy as np
        if np.__version__.startswith('2.'):
            logger.warning("檢測到 NumPy 2.0+，可能影響訓練")
            print("⚠️  檢測到 NumPy 2.0+，如果遇到錯誤，請考慮降級")
        
        from scripts.train_rag import RAGTrainer
        trainer = RAGTrainer()
        await trainer.run_training_pipeline()
        logger.info("✓ RAG 系統訓練完成")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ RAG 系統訓練失敗: {error_msg}")
        
        # 檢查是否為 NumPy 相關錯誤
        if "np.float_" in error_msg or "numpy" in error_msg.lower():
            print("❌ 檢測到 NumPy 相容性錯誤")
            print("建議執行以下命令修復:")
            print("pip install numpy==1.25.2 --force-reinstall")
            print("pip install sentence-transformers --force-reinstall")
            print("pip install chromadb --force-reinstall")
        
        import traceback
        logger.error(traceback.format_exc())
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
        import traceback
        logger.error(traceback.format_exc())
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
        
        print("\n" + "="*60)
        print("🌐 正在啟動 FastAPI 網頁服務器...")
        print("="*60)
        print(f"🏠 服務器地址: http://localhost:8000")
        print(f"📖 API 文檔: http://localhost:8000/docs")
        print(f"📊 系統狀態: http://localhost:8000/api/status")
        print(f"💬 RAG 聊天: POST /api/chat")
        print(f"🚦 交通顧問: POST /api/controller/chat")
        print("="*60)
        print("⚠️  按 Ctrl+C 停止服務器")
        print("="*60)
        
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
    
    print("\n" + "="*60)
    print("💬 啟動命令行聊天模式")
    print("="*60)
    print("✨ 您可以直接詢問關於高速公路的問題")
    print("🔍 系統會使用 RAG 技術提供基於資料的回答")
    print("⚠️  輸入 'quit', 'exit' 或按 Ctrl+C 退出")
    print("="*60)
    
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
        print("\n💬 聊天會話已結束")
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
    print("   - 可通過瀏覽器訪問 API 文檔")
    print("   - 支援前端應用整合")
    print()
    print("2. 啟動命令行聊天")
    print("   - 直接在終端中對話")
    print("   - 適合快速測試和驗證")
    print("   - 輕量級互動模式")
    print()
    print("3. 重新訓練系統")
    print("   - 重新處理資料並訓練")
    print("   - 適合更新資料後使用")
    print("   - 重建向量資料庫")
    print()
    print("4. 修復相容性問題")
    print("   - 修復 NumPy 相容性")
    print("   - 重新安裝問題套件")
    print("   - 診斷環境問題")
    print()
    print("5. 退出")
    print("="*60)

async def fix_compatibility_issues():
    """修復相容性問題"""
    print("\n🔧 開始修復相容性問題...")
    
    # 1. 修復 NumPy
    if not fix_numpy_version():
        print("❌ NumPy 修復失敗")
        return False
    
    # 2. 重新安裝依賴
    if not install_python_dependencies():
        print("❌ 依賴重新安裝失敗")
        return False
    
    print("✓ 相容性問題修復完成")
    return True

async def main():
    """主函數"""
    print("🚀 RAG 系統整合啟動腳本 (NumPy 相容性修復版)")
    print("="*50)
    
    # 0. 檢查 NumPy 相容性
    logger.info("步驟 0: 檢查 NumPy 相容性...")
    if not check_numpy_compatibility():
        print("❌ NumPy 相容性檢查失敗")
        return
    
    # 1. 檢查 Ollama 安裝
    logger.info("步驟 1: 檢查 Ollama 安裝...")
    if not check_ollama_installation():
        logger.error("請先安裝 Ollama: https://ollama.ai")
        print("\n❌ 未檢測到 Ollama 安裝")
        print("請先安裝 Ollama:")
        print("1. 訪問 https://ollama.ai")
        print("2. 下載並安裝對應系統的版本")
        print("3. 重新執行此腳本")
        return
    
    # 2. 檢查 Ollama 服務
    logger.info("步驟 2: 檢查 Ollama 服務...")
    service_running, models = check_ollama_service()
    if not service_running:
        logger.error("請啟動 Ollama 服務: ollama serve")
        print("\n❌ Ollama 服務未運行")
        print("請在新終端執行: ollama serve")
        print("然後重新執行此腳本")
        return
    
    # 3. 檢查並下載模型
    if not models:
        logger.info("步驟 3: 下載推薦模型...")
        print("\n⏬ 正在下載推薦模型...")
        model = download_recommended_model()
        if not model:
            print("❌ 模型下載失敗，請手動執行:")
            print("ollama pull qwen2.5:7b")
            return
    else:
        logger.info("✓ 已有可用模型")
        print(f"✓ 檢測到 {len(models)} 個可用模型")
    
    # 4. 安裝 Python 依賴
    logger.info("步驟 4: 檢查 Python 依賴...")
    if not install_python_dependencies():
        print("❌ Python 依賴安裝失敗")
        return
    
    # 5. 檢查資料文件
    logger.info("步驟 5: 檢查資料文件...")
    if not check_data_files():
        print("❌ 資料文件檢查失敗")
        return
    
    # 6. 訓練 RAG 系統
    logger.info("步驟 6: 訓練 RAG 系統...")
    print("\n🎓 開始訓練 RAG 系統...")
    if not await run_rag_training():
        logger.warning("訓練失敗，嘗試僅測試系統...")
        print("⚠️  訓練失敗，嘗試測試現有系統...")
        if not await test_rag_system():
            logger.error("系統測試也失敗，請檢查配置")
            print("❌ 系統測試失敗，建議選擇選項 4 修復相容性問題")
            # 不直接 return，讓用戶可以選擇修復
    
    # 7. 顯示使用說明
    print_usage_instructions()
    
    # 8. 顯示操作選單並處理用戶選擇
    while True:
        try:
            show_operation_menu()
            choice = input("\n請輸入選擇 (1-5): ").strip()
            
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
                print("\n🔄 開始重新訓練系統...")
                success = await run_rag_training()
                if success:
                    print("\n✓ 重新訓練完成！")
                else:
                    print("\n✗ 重新訓練失敗，建議嘗試選項 4 修復相容性問題")
                continue
            
            elif choice == "4":
                logger.info("用戶選擇：修復相容性問題")
                success = await fix_compatibility_issues()
                if success:
                    print("\n✓ 相容性問題修復完成，建議重新訓練系統")
                else:
                    print("\n✗ 相容性問題修復失敗")
                input("\n按 Enter 返回選單...")
                continue
                
            elif choice == "5":
                logger.info("用戶選擇：退出")
                print("再見！")
                break
                
            else:
                print("無效選擇，請輸入 1-5")
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