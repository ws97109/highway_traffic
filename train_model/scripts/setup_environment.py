"""
環境設置腳本
用於初始化 RAG 訓練環境
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from loguru import logger

class EnvironmentSetup:
    """環境設置類"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.train_model_dir = Path(__file__).parent.parent
        
    def check_python_version(self):
        """檢查 Python 版本"""
        logger.info("檢查 Python 版本...")
        version = sys.version_info
        
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error("需要 Python 3.8 或更高版本")
            return False
        
        logger.info(f"Python 版本: {version.major}.{version.minor}.{version.micro} ✓")
        return True
    
    def check_ollama_installation(self):
        """檢查 Ollama 安裝"""
        logger.info("檢查 Ollama 安裝...")
        
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Ollama 已安裝: {result.stdout.strip()} ✓")
                return True
            else:
                logger.error("Ollama 未正確安裝")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.error("找不到 Ollama 命令，請先安裝 Ollama")
            self._show_ollama_install_instructions()
            return False
    
    def _show_ollama_install_instructions(self):
        """顯示 Ollama 安裝說明"""
        logger.info("Ollama 安裝說明:")
        logger.info("1. macOS/Linux: curl -fsSL https://ollama.ai/install.sh | sh")
        logger.info("2. Windows: 下載並安裝 https://ollama.ai/download")
        logger.info("3. 安裝後執行: ollama pull qwen2.5:14b")
    
    async def check_ollama_service(self):
        """檢查 Ollama 服務狀態"""
        logger.info("檢查 Ollama 服務...")
        
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    models = response.json()
                    available_models = [m['name'] for m in models.get('models', [])]
                    logger.info(f"Ollama 服務正常，可用模型: {available_models} ✓")
                    
                    if 'qwen2.5:14b' not in available_models:
                        logger.warning("未找到 qwen2.5:14b 模型")
                        logger.info("請執行: ollama pull qwen2.5:14b")
                        return False
                    
                    return True
                else:
                    logger.error("Ollama 服務回應異常")
                    return False
        except Exception as e:
            logger.error(f"無法連接 Ollama 服務: {e}")
            logger.info("請執行: ollama serve")
            return False
    
    def install_dependencies(self):
        """安裝 Python 依賴"""
        logger.info("安裝 Python 依賴...")
        
        requirements_file = self.train_model_dir / "requirements.txt"
        
        if not requirements_file.exists():
            logger.error("找不到 requirements.txt 文件")
            return False
        
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("Python 依賴安裝成功 ✓")
                return True
            else:
                logger.error(f"依賴安裝失敗: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("依賴安裝超時")
            return False
        except Exception as e:
            logger.error(f"安裝依賴時發生錯誤: {e}")
            return False
    
    def create_directories(self):
        """創建必要的目錄"""
        logger.info("創建必要的目錄...")
        
        directories = [
            self.train_model_dir / "vector_db",
            self.train_model_dir / "processed_data", 
            self.train_model_dir / "logs",
            self.train_model_dir / "evaluation_results"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"創建目錄: {directory}")
        
        logger.info("目錄創建完成 ✓")
        return True
    
    def check_data_files(self):
        """檢查訓練資料文件"""
        logger.info("檢查訓練資料文件...")
        
        data_dir = self.project_root / "data" / "Taiwan"
        required_files = [
            "國道一號_整合資料.csv",
            "國道三號_整合資料.csv"
        ]
        
        missing_files = []
        for filename in required_files:
            file_path = data_dir / filename
            if file_path.exists():
                logger.info(f"找到資料文件: {filename} ✓")
            else:
                logger.error(f"缺少資料文件: {filename}")
                missing_files.append(filename)
        
        if missing_files:
            logger.error(f"缺少 {len(missing_files)} 個必要的資料文件")
            return False
        
        return True
    
    def check_env_config(self):
        """檢查環境配置"""
        logger.info("檢查環境配置...")
        
        env_file = self.project_root / ".env"
        if not env_file.exists():
            logger.error("找不到 .env 配置文件")
            return False
        
        # 讀取 .env 文件檢查必要配置
        required_configs = [
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL",
            "TRAIN_DATA_PATH"
        ]
        
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        missing_configs = []
        for config in required_configs:
            if config not in env_content or f"{config}=" not in env_content:
                missing_configs.append(config)
        
        if missing_configs:
            logger.error(f"環境配置缺少: {missing_configs}")
            return False
        
        logger.info("環境配置檢查完成 ✓")
        return True
    
    def run_quick_test(self):
        """執行快速測試"""
        logger.info("執行快速功能測試...")
        
        try:
            # 測試導入主要模組
            sys.path.insert(0, str(self.train_model_dir))
            
            from data_processing.csv_processor import HighwayCSVProcessor
            from embeddings.vector_store import VectorStore
            from models.ollama_client import OllamaClient
            
            logger.info("模組導入測試成功 ✓")
            return True
            
        except ImportError as e:
            logger.error(f"模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"測試執行失敗: {e}")
            return False
    
    async def setup_complete_environment(self):
        """執行完整環境設置"""
        logger.info("開始 RAG 訓練環境設置...")
        
        steps = [
            ("Python 版本檢查", self.check_python_version),
            ("Ollama 安裝檢查", self.check_ollama_installation), 
            ("創建目錄結構", self.create_directories),
            ("安裝 Python 依賴", self.install_dependencies),
            ("檢查資料文件", self.check_data_files),
            ("檢查環境配置", self.check_env_config),
            ("執行快速測試", self.run_quick_test),
        ]
        
        # 執行同步步驟
        for step_name, step_func in steps:
            logger.info(f"\n--- {step_name} ---")
            if not step_func():
                logger.error(f"環境設置失敗於: {step_name}")
                return False
        
        # 執行異步步驟
        logger.info("\n--- Ollama 服務檢查 ---")
        if not await self.check_ollama_service():
            logger.error("環境設置失敗於: Ollama 服務檢查")
            return False
        
        logger.info("\n" + "="*50)
        logger.info("🎉 RAG 訓練環境設置完成！")
        logger.info("="*50)
        logger.info("下一步:")
        logger.info("1. cd train_model")
        logger.info("2. python scripts/train_rag.py --mode train")
        logger.info("="*50)
        
        return True

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 訓練環境設置")
    parser.add_argument("--quick", action="store_true", help="僅執行快速檢查")
    parser.add_argument("--install-deps", action="store_true", help="僅安裝依賴")
    
    args = parser.parse_args()
    
    # 配置日誌
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    
    setup = EnvironmentSetup()
    
    async def run_setup():
        if args.quick:
            # 快速檢查
            checks = [
                setup.check_python_version(),
                setup.check_ollama_installation(),
                await setup.check_ollama_service(),
                setup.run_quick_test()
            ]
            if all(checks):
                logger.info("✓ 快速檢查全部通過")
            else:
                logger.error("✗ 快速檢查發現問題")
                
        elif args.install_deps:
            # 僅安裝依賴
            setup.install_dependencies()
            
        else:
            # 完整設置
            await setup.setup_complete_environment()
    
    # 執行設置
    try:
        asyncio.run(run_setup())
    except KeyboardInterrupt:
        logger.info("設置被用戶中斷")
    except Exception as e:
        logger.error(f"設置過程發生錯誤: {e}")

if __name__ == "__main__":
    main()