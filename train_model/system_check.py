#!/usr/bin/env python3
"""
RAG 系統健康檢查腳本
檢查所有組件的狀態和可用性
"""

import os
import sys
import asyncio
import subprocess
import importlib
from pathlib import Path
from loguru import logger

# 添加專案路徑
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

class HealthChecker:
    """系統健康檢查器"""
    
    def __init__(self):
        self.checks_passed = 0
        self.total_checks = 0
        self.errors = []
        self.warnings = []
    
    def check(self, name: str, success: bool, message: str = "", error: str = ""):
        """記錄檢查結果"""
        self.total_checks += 1
        
        if success:
            self.checks_passed += 1
            status = "✓"
            color = "green"
        else:
            status = "✗"
            color = "red"
            if error:
                self.errors.append(f"{name}: {error}")
        
        # 格式化輸出
        print(f"{status} {name:<40} {message}")
        
        if error and not success:
            print(f"   錯誤: {error}")
    
    def warn(self, message: str):
        """記錄警告"""
        self.warnings.append(message)
        print(f"⚠ {message}")
    
    def summary(self):
        """顯示檢查摘要"""
        print("\\n" + "="*60)
        print(f"系統健康檢查完成: {self.checks_passed}/{self.total_checks} 項通過")
        
        success_rate = (self.checks_passed / self.total_checks * 100) if self.total_checks > 0 else 0
        
        if success_rate == 100:
            print("🎉 系統狀態良好，所有檢查都通過了！")
            return True
        elif success_rate >= 80:
            print("⚠ 系統大部分功能正常，但有一些問題需要注意")
        else:
            print("❌ 系統存在重要問題，建議修復後再使用")
        
        if self.errors:
            print("\\n主要錯誤:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\\n警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        return success_rate >= 80

async def check_python_environment(checker: HealthChecker):
    """檢查 Python 環境"""
    print("\\n📋 Python 環境檢查")
    print("-" * 40)
    
    # Python 版本
    python_version = sys.version_info
    if python_version >= (3, 8):
        checker.check("Python 版本", True, f"{python_version.major}.{python_version.minor}")
    else:
        checker.check("Python 版本", False, 
                     f"{python_version.major}.{python_version.minor}",
                     "需要 Python 3.8 或更高版本")
    
    # 必要套件
    required_packages = [
        ('torch', 'PyTorch'),
        ('sentence_transformers', 'Sentence Transformers'), 
        ('chromadb', 'ChromaDB'),
        ('httpx', 'HTTPX'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('loguru', 'Loguru'),
        ('yaml', 'PyYAML')
    ]
    
    for package_name, display_name in required_packages:
        try:
            importlib.import_module(package_name)
            checker.check(f"{display_name} 套件", True)
        except ImportError:
            checker.check(f"{display_name} 套件", False, 
                         error=f"請安裝: pip install {package_name}")

async def check_ollama_service(checker: HealthChecker):
    """檢查 Ollama 服務"""
    print("\\n🤖 Ollama 服務檢查")
    print("-" * 40)
    
    # Ollama 命令可用性
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            checker.check("Ollama 安裝", True, version)
        else:
            checker.check("Ollama 安裝", False, error="Ollama 命令執行失敗")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        checker.check("Ollama 安裝", False, error="未找到 ollama 命令")
        return
    
    # Ollama 服務狀態
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                checker.check("Ollama 服務", True, f"運行中，{len(models)} 個模型")
                
                # 檢查推薦模型
                model_names = [model['name'] for model in models]
                recommended_models = ['qwen2.5:14b', 'qwen2.5:14b', 'llama3:latest']
                
                found_model = False
                for rec_model in recommended_models:
                    if any(rec_model in model_name for model_name in model_names):
                        checker.check(f"推薦模型 ({rec_model})", True)
                        found_model = True
                        break
                
                if not found_model and models:
                    checker.warn(f"建議下載推薦模型，當前模型: {model_names}")
                elif not models:
                    checker.check("可用模型", False, error="沒有可用模型")
                    
            else:
                checker.check("Ollama 服務", False, 
                             error=f"服務響應異常: {response.status_code}")
    except Exception as e:
        checker.check("Ollama 服務", False, error=f"無法連接服務: {e}")

async def check_data_files(checker: HealthChecker):
    """檢查資料文件"""
    print("\\n📊 資料文件檢查")
    print("-" * 40)
    
    # 檢查資料目錄
    data_dir = current_dir.parent / "data" / "Taiwan"
    checker.check("資料目錄", data_dir.exists(), str(data_dir))
    
    if data_dir.exists():
        required_files = [
            "國道一號_整合資料.csv",
            "國道三號_整合資料.csv"
        ]
        
        for file_name in required_files:
            file_path = data_dir / file_name
            if file_path.exists():
                file_size = file_path.stat().st_size
                checker.check(f"資料文件: {file_name}", True, 
                             f"{file_size:,} bytes")
            else:
                checker.check(f"資料文件: {file_name}", False,
                             error="文件不存在")

async def check_config_system(checker: HealthChecker):
    """檢查配置系統"""
    print("\\n⚙️  配置系統檢查")
    print("-" * 40)
    
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        checker.check("配置管理器", True)
        
        # 檢查配置文件
        config_path = Path(config_manager.config_path)
        checker.check("配置文件", config_path.exists(), str(config_path))
        
        # 檢查關鍵配置段
        config = config_manager.get_config()
        required_sections = ['ollama', 'embeddings', 'vector_db', 'data_processing']
        
        for section in required_sections:
            if section in config:
                checker.check(f"配置段: {section}", True)
            else:
                checker.check(f"配置段: {section}", False, error="配置段缺失")
                
    except Exception as e:
        checker.check("配置系統", False, error=str(e))

async def check_rag_components(checker: HealthChecker):
    """檢查 RAG 組件"""
    print("\\n🧠 RAG 組件檢查")
    print("-" * 40)
    
    try:
        # 向量存儲
        from embeddings.vector_store import VectorStore
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        
        if 'error' in stats:
            checker.check("向量存儲", False, error=stats['error'])
        else:
            doc_count = stats.get('document_count', 0)
            checker.check("向量存儲", True, f"{doc_count} 個文檔")
            
            if doc_count == 0:
                checker.warn("向量數據庫為空，需要先訓練系統")
        
        # Ollama 客戶端
        from models.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        
        connection_ok = await ollama_client.check_connection()
        checker.check("Ollama 客戶端", connection_ok)
        
        # CSV 處理器
        from data_processing.csv_processor import HighwayCSVProcessor
        csv_processor = HighwayCSVProcessor()
        checker.check("CSV 處理器", True)
        
    except Exception as e:
        checker.check("RAG 組件", False, error=str(e))

async def check_system_resources(checker: HealthChecker):
    """檢查系統資源"""
    print("\\n💾 系統資源檢查")
    print("-" * 40)
    
    try:
        import psutil
        
        # 記憶體
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        if memory_gb >= 8:
            checker.check("總記憶體", True, f"{memory_gb:.1f} GB")
        else:
            checker.check("總記憶體", False, f"{memory_gb:.1f} GB", 
                         "建議至少 8GB 記憶體")
        
        if memory_available_gb >= 4:
            checker.check("可用記憶體", True, f"{memory_available_gb:.1f} GB")
        else:
            checker.warn(f"可用記憶體較少: {memory_available_gb:.1f} GB")
        
        # 硬碟空間
        disk = psutil.disk_usage(str(current_dir))
        disk_free_gb = disk.free / (1024**3)
        
        if disk_free_gb >= 10:
            checker.check("可用硬碟空間", True, f"{disk_free_gb:.1f} GB")
        else:
            checker.check("可用硬碟空間", False, f"{disk_free_gb:.1f} GB",
                         "建議至少 10GB 可用空間")
            
    except ImportError:
        checker.warn("psutil 未安裝，無法檢查系統資源")
    except Exception as e:
        checker.warn(f"系統資源檢查失敗: {e}")

async def main():
    """主函數"""
    print("🔍 RAG 系統健康檢查")
    print("="*60)
    
    checker = HealthChecker()
    
    # 執行各項檢查
    await check_python_environment(checker)
    await check_ollama_service(checker)
    await check_data_files(checker)
    await check_config_system(checker)
    await check_rag_components(checker)
    await check_system_resources(checker)
    
    # 顯示摘要
    system_ok = checker.summary()
    
    if system_ok:
        print("\\n🚀 系統準備就緒！您可以：")
        print("1. 運行 python quick_start.py 快速開始")
        print("2. 運行 python scripts/train_rag.py --mode chat 開始對話")
    else:
        print("\\n🔧 請先解決上述問題再使用系統")
        print("參考文檔: RAG_啟用指南.md")

if __name__ == "__main__":
    asyncio.run(main())