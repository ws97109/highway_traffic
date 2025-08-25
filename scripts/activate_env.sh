#!/bin/bash
# Highway Traffic System Environment Activation Script
# 高速公路交通系統環境激活腳本

echo "🚀 激活高速公路交通系統環境..."
echo "Activating Highway Traffic System Environment..."

# 激活 conda 環境
conda activate highway-traffic-system

# 檢查激活是否成功
if [ $? -eq 0 ]; then
    echo "✅ 環境激活成功！"
    echo "Environment activated successfully!"
    
    echo ""
    echo "📍 當前環境信息："
    echo "Current Environment Info:"
    echo "  - 環境名稱: highway-traffic-system"
    echo "  - Python 版本: $(python --version)"
    echo "  - 環境路徑: $CONDA_PREFIX"
    
    echo ""
    echo "🔧 可用命令："
    echo "Available Commands:"
    echo "  - python check_environment.py  # 檢查環境"
    echo "  - cd src/models/mt_stnet && python run_train.py  # 訓練 MT-STNet 模型"
    echo "  - jupyter notebook  # 啟動 Jupyter Notebook"
    echo ""
    
    echo "🎯 專案目錄："
    echo "Project Directory:"
    pwd
    
    echo ""
    echo "💡 提示: 使用 'conda deactivate' 可以退出此環境"
    echo "Tip: Use 'conda deactivate' to exit this environment"
    
else
    echo "❌ 環境激活失敗！"
    echo "Environment activation failed!"
    echo "請確保已經安裝了 conda 並且環境 'highway-traffic-system' 存在"
    echo "Please make sure conda is installed and environment 'highway-traffic-system' exists"
fi
