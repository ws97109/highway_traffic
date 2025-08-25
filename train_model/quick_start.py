#!/usr/bin/env python3
"""
RAG 系統快速啟動腳本
提供一鍵式部署和測試功能
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from loguru import logger

# 添加專案路徑
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def check_ollama_installation():
    """檢查 Ollama 是否安裝"""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"✓ Ollama 已安裝: {result.stdout.strip()}")
            return True
        else:
            logger.error("✗ Ollama 未正確安裝")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error("✗ 找不到 Ollama 命令")
        return False

def check_ollama_service():
    """檢查 Ollama 服務是否運行"""
    try:
        import httpx
        client = httpx.Client(timeout=5)
        response = client.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            logger.info(f"✓ Ollama 服務運行正常，可用模型數量: {len(models)}")
            for model in models:
                logger.info(f"  - {model['name']}")
            return True, models
        else:
            logger.error("✗ Ollama 服務未響應")
            return False, []
    except Exception as e:
        logger.error(f"✗ 無法連接 Ollama 服務: {e}")
        return False, []

def install_python_dependencies():
    """安裝 Python 依賴"""
    logger.info("正在安裝 Python 依賴...")
    requirements_file = current_dir / "requirements.txt"
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        logger.info("✓ Python 依賴安裝完成")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Python 依賴安裝失敗: {e}")
        return False

def download_recommended_model():
    """下載推薦的模型"""
    logger.info("正在下載推薦的 Ollama 模型...")
    
    # 推薦的模型列表（按性能和資源需求排序）
    recommended_models = [
        "deepseek-r1:32b",  # 平衡性能和資源
        "llama3:latest", # 備選方案
        "mistral:latest"  # 輕量級選項
    ]
    
    for model in recommended_models:
        try:
            logger.info(f"嘗試下載模型: {model}")
            result = subprocess.run([
                'ollama', 'pull', model
            ], timeout=1200, capture_output=True, text=True)  # 20分鐘超時
            
            if result.returncode == 0:
                logger.info(f"✓ 成功下載模型: {model}")
                return model
            else:
                logger.warning(f"下載模型 {model} 失敗: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning(f"下載模型 {model} 超時")
        except Exception as e:
            logger.error(f"下載模型 {model} 時發生錯誤: {e}")
    
    logger.error("✗ 無法下載任何推薦模型")
    return None

def check_data_files():
    """檢查必要的資料文件"""
    data_dir = current_dir.parent / "data" / "Taiwan"
    required_files = [
        "國道一號_整合資料.csv",
        "國道三號_整合資料.csv"
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
    print("\\n" + "="*60)
    print("🚗 高速公路 RAG 系統啟動完成！")
    print("="*60)
    print("\\n可用命令：")
    print("1. 啟動互動聊天：")
    print("   python scripts/train_rag.py --mode chat")
    print("\\n2. 重新訓練系統：")
    print("   python scripts/train_rag.py --mode train --force-rebuild")
    print("\\n3. 僅測試系統：")
    print("   python scripts/train_rag.py --mode test")
    print("\\n示例問題：")
    print("- 國道一號的車道寬度通常是多少？")
    print("- 國道三號和國道一號在路面設計上有什麼不同？")
    print("- 高速公路的縱向坡度一般是多少？")
    print("\\n" + "="*60)

async def main():
    """主函數"""
    print("🚀 RAG 系統快速啟動腳本")
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
    
    # 8. 詢問是否啟動聊天
    try:
        response = input("\\n是否立即啟動互動聊天？(y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            logger.info("啟動互動聊天...")
            import importlib
            train_rag_module = importlib.import_module('scripts.train_rag')
            RAGTrainer = train_rag_module.RAGTrainer
            
            trainer = RAGTrainer()
            await trainer.setup_components()
            await trainer.interactive_chat()
    except KeyboardInterrupt:
        logger.info("用戶取消操作")
    except Exception as e:
        logger.error(f"啟動聊天模式失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())