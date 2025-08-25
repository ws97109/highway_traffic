"""
配置管理模組
統一處理配置文件路徑和載入
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_name: str = "rag_config.yaml"):
        """初始化配置管理器"""
        self.config_name = config_name
        self.config_path = self._find_config_file()
        self.config = self._load_config()
        
    def _find_config_file(self) -> str:
        """找到配置文件的絕對路徑"""
        # 首先檢查環境變數
        if 'RAG_CONFIG_PATH' in os.environ:
            config_path = os.environ['RAG_CONFIG_PATH']
            if os.path.exists(config_path):
                logger.info(f"使用環境變數指定的配置文件: {config_path}")
                return config_path
        
        # 搜索可能的配置文件位置
        current_file = Path(__file__)
        possible_paths = [
            # 當前目錄
            Path.cwd() / self.config_name,
            # train_model/configs 目錄
            current_file.parent.parent / "configs" / self.config_name,
            # 專案根目錄的 configs
            current_file.parent.parent.parent / "configs" / self.config_name,
            # 同級 configs 目錄
            current_file.parent / "configs" / self.config_name,
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"找到配置文件: {path}")
                return str(path.resolve())
        
        # 如果都找不到，創建預設配置文件
        default_path = current_file.parent.parent / "configs" / self.config_name
        logger.warning(f"未找到配置文件，將在 {default_path} 創建預設配置")
        self._create_default_config(default_path)
        return str(default_path.resolve())
    
    def _create_default_config(self, config_path: Path):
        """創建預設配置文件"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'deepseek-r1:32b',  # 改為較小的模型
                'timeout': 300,
                'max_tokens': 2048,
                'temperature': 0.1
            },
            'embeddings': {
                'model_name': 'all-MiniLM-L6-v2',
                'device': 'cpu',
                'batch_size': 32,
                'max_length': 512
            },
            'chunking': {
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'separators': ['\n\n', '\n', '。', '；', '，', ' ']
            },
            'vector_db': {
                'type': 'chroma',
                'persist_directory': './vector_db',
                'collection_name': 'highway_traffic',
                'distance_metric': 'cosine'
            },
            'retrieval': {
                'top_k': 5,
                'score_threshold': 0.7,
                'rerank': False
            },
            'data_processing': {
                'input_data_path': '../data/Taiwan',
                'highway1_file': '國道一號_整合資料.csv',
                'highway3_file': '國道三號_整合資料.csv',
                'output_dir': './processed_data'
            },
            'training': {
                'epochs': 5,
                'batch_size': 8,
                'learning_rate': 2e-5,
                'save_steps': 500,
                'eval_steps': 100,
                'warmup_steps': 100,
                'max_seq_length': 2048
            },
            'evaluation': {
                'test_size': 0.2,
                'metrics': ['accuracy', 'bleu', 'rouge']
            },
            'logging': {
                'level': 'INFO',
                'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
                'file': 'rag_training.log'
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"已創建預設配置文件: {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"成功載入配置文件: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"載入配置文件失敗: {e}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """獲取完整配置"""
        return self.config
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """獲取配置的特定部分"""
        return self.config.get(section_name, {})
    
    def get_value(self, section: str, key: str, default=None):
        """獲取特定配置值"""
        return self.config.get(section, {}).get(key, default)
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        self.config.update(updates)
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"配置已保存到: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失敗: {e}")
            raise
    
    def resolve_path(self, path: str) -> str:
        """解析相對路徑為絕對路徑"""
        if os.path.isabs(path):
            return path
        
        # 相對於配置文件目錄
        config_dir = Path(self.config_path).parent
        resolved_path = config_dir / path
        return str(resolved_path.resolve())

# 全域配置管理器實例
_config_manager = None

def get_config_manager(config_name: str = "rag_config.yaml") -> ConfigManager:
    """獲取全域配置管理器實例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_name)
    return _config_manager

def get_config() -> Dict[str, Any]:
    """快速獲取配置"""
    return get_config_manager().get_config()

if __name__ == "__main__":
    # 測試配置管理器
    config_manager = ConfigManager()
    print(f"配置文件路徑: {config_manager.config_path}")
    print(f"Ollama 設定: {config_manager.get_section('ollama')}")