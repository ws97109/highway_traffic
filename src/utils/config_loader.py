import os
import json
import re
from typing import Any, Dict


def load_env_file(env_path: str = '.env') -> Dict[str, str]:
    """載入 .env 檔案中的環境變數"""
    env_vars = {}
    
    # 如果檔案不存在，返回空字典
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳過空行和註解
            if not line or line.startswith('#'):
                continue
            
            # 解析 KEY=VALUE 格式
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def replace_env_variables(obj: Any, env_vars: Dict[str, str]) -> Any:
    """遞歸替換物件中的環境變數佔位符"""
    if isinstance(obj, dict):
        return {key: replace_env_variables(value, env_vars) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [replace_env_variables(item, env_vars) for item in obj]
    elif isinstance(obj, str):
        # 替換 ${VAR_NAME} 格式的變數
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
        
        def replace_match(match):
            var_name = match.group(1)
            # 優先使用 .env 檔案中的值，然後是系統環境變數
            return env_vars.get(var_name, os.environ.get(var_name, match.group(0)))
        
        return re.sub(pattern, replace_match, obj)
    else:
        return obj


def load_config_with_env(config_path: str, env_path: str = '.env') -> Dict[str, Any]:
    """載入配置檔案並替換環境變數"""
    # 載入環境變數
    env_vars = load_env_file(env_path)
    
    # 載入配置檔案
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 替換環境變數
    return replace_env_variables(config, env_vars)


def get_config_value(config: Dict[str, Any], key_path: str) -> Any:
    """使用點分隔的路徑獲取配置值
    例如: get_config_value(config, 'warning_config.json.email.username')
    注意：如果鍵本身包含點號，請直接使用字典索引方式
    """
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    
    return value


if __name__ == "__main__":
    # 測試配置載入
    try:
        # 確保路徑正確
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        
        config_path = os.path.join(project_root, 'data', 'config', 'system_config.json')
        env_path = os.path.join(project_root, '.env')
        
        print("=== 測試配置載入器 ===")
        print(f"配置檔案路徑: {config_path}")
        print(f"環境檔案路徑: {env_path}")
        
        # 載入配置
        config = load_config_with_env(config_path, env_path)
        print("✅ 配置載入成功！")
        
        # 測試關鍵配置值
        email_username = config['warning_config.json']['email']['username']
        email_password = config['warning_config.json']['email']['password']
        api_key = config['location_config.json']['google_maps']['api_key']
        
        print(f"✅ 電子郵件用戶名: {email_username}")
        print(f"✅ 電子郵件密碼: {'*' * len(email_password)}")
        print(f"✅ Google Maps API Key: {api_key[:10]}...{api_key[-10:]}")
        
        print("\n配置載入器測試通過！環境變數已正確替換。")
        
    except Exception as e:
        print(f"❌ 配置載入失敗: {e}")
        import traceback
        traceback.print_exc()
