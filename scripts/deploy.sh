#!/bin/bash

# 交通衝擊波預測系統 - 完整部署腳本
# 包含後端 API 和前端應用的部署

echo "🚀 開始部署交通衝擊波預測系統..."

# 檢查必要的工具
check_requirements() {
    echo "📋 檢查系統需求..."
    
    # 檢查 Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 未安裝"
        exit 1
    fi
    
    # 檢查 Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js 未安裝"
        exit 1
    fi
    
    # 檢查 npm
    if ! command -v npm &> /dev/null; then
        echo "❌ npm 未安裝" 
        exit 1
    fi
    
    echo "✅ 系統需求檢查完成"
}

# 設定環境變數
setup_environment() {
    echo "🔧 設定環境變數..."
    
    # 檢查 .env 檔案是否存在
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "📄 已複製 .env.example 到 .env"
            echo "⚠️  請編輯 .env 檔案並填入您的 API 金鑰"
            echo ""
            echo "需要設定的項目："
            echo "- TDX_CLIENT_ID: 交通部 TDX API 用戶端 ID"
            echo "- TDX_CLIENT_SECRET: 交通部 TDX API 用戶端密鑰"
            echo "- GOOGLE_MAPS_API_KEY: Google Maps API 金鑰"
            echo "- EMAIL_USERNAME: 電子郵件帳號 (用於警告通知)"
            echo "- EMAIL_PASSWORD: 電子郵件密碼"
            echo ""
            read -p "請設定完 .env 檔案後按 Enter 繼續..."
        else
            echo "❌ 找不到 .env.example 檔案"
            exit 1
        fi
    fi
    
    # 設定前端環境變數
    if [ ! -f "frontend/.env.local" ]; then
        echo "📄 建立前端環境變數檔案..."
        cat > frontend/.env.local << EOF
# 前端環境變數
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=\${GOOGLE_MAPS_API_KEY}
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=交通衝擊波預測系統
NEXT_PUBLIC_DEFAULT_LAT=25.0330
NEXT_PUBLIC_DEFAULT_LNG=121.5654
NEXT_PUBLIC_DEFAULT_ZOOM=10
EOF
        echo "✅ 前端環境變數檔案已建立"
    fi
}

# 安裝後端依賴
install_backend_dependencies() {
    echo "📦 安裝後端依賴..."
    
    # 安裝必要套件
    pip install -r requirements.txt 2>/dev/null || {
        echo "📋 建立 requirements.txt..."
        cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-multipart==0.0.6
pandas==2.1.3
numpy==1.25.2
scikit-learn==1.3.2
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.5.0
matplotlib==3.8.2
seaborn==0.13.0
plotly==5.17.0
sqlite3
aiofiles==23.2.1
python-jose[cryptography]==3.3.0
python-socketio==5.9.0
asyncio-mqtt==0.16.1
EOF
        pip install -r requirements.txt
    }
    
    echo "✅ 後端依賴安裝完成"
}

# 安裝前端依賴
install_frontend_dependencies() {
    echo "📦 安裝前端依賴..."
    
    cd frontend
    
    # 檢查 package.json 是否存在
    if [ ! -f "package.json" ]; then
        echo "🔧 初始化前端專案..."
        npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias="@/*" --yes
    fi
    
    # 安裝額外依賴
    npm install @types/leaflet leaflet react-leaflet
    npm install recharts chart.js react-chartjs-2
    npm install @heroicons/react
    npm install socket.io-client
    npm install axios
    npm install date-fns
    npm install react-hook-form
    npm install @hookform/resolvers yup
    npm install @googlemaps/js-api-loader
    
    # 安裝開發依賴
    npm install -D @types/socket.io-client
    
    cd ..
    echo "✅ 前端依賴安裝完成"
}

# 建立必要目錄
create_directories() {
    echo "📁 建立必要目錄..."
    
    # 後端目錄
    mkdir -p logs
    mkdir -p data/{raw,processed,config}
    mkdir -p temp
    mkdir -p backups
    
    # API 目錄
    mkdir -p api/{routes,models,middleware}
    
    # 建立空的 __init__.py 檔案
    touch api/__init__.py
    touch api/routes/__init__.py
    touch api/models/__init__.py
    touch api/middleware/__init__.py
    
    echo "✅ 目錄結構建立完成"
}

# 測試後端系統
test_backend() {
    echo "🧪 測試後端系統..."
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 測試模組導入
    python -c "
try:
    from src.core.integrated_system import IntegratedShockPredictionSystem
    from src.detection.final_optimized_detector import FinalOptimizedShockDetector
    from src.prediction.realtime_shock_predictor import RealtimeShockPredictor
    print('✅ 後端模組導入測試通過')
except ImportError as e:
    print(f'❌ 後端模組導入失敗: {e}')
    exit(1)
"
    
    echo "✅ 後端系統測試完成"
}

# 建置前端
build_frontend() {
    echo "🔨 建置前端應用..."
    
    cd frontend
    
    # 建置應用
    npm run build
    
    cd ..
    echo "✅ 前端建置完成"
}

# 啟動服務
start_services() {
    echo "🚀 啟動服務..."
    
    # 啟動後端 API
    echo "🔧 啟動後端 API (Port 8000)..."
    source venv/bin/activate
    nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > api.pid
    
    # 等待 API 啟動
    sleep 5
    
    # 檢查 API 是否正常
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ 後端 API 啟動成功"
    else
        echo "❌ 後端 API 啟動失敗"
        cat logs/api.log
        exit 1
    fi
    
    # 啟動前端應用
    echo "🔧 啟動前端應用 (Port 3000)..."
    cd frontend
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    cd ..
    
    # 等待前端啟動
    sleep 10
    
    # 檢查前端是否正常
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ 前端應用啟動成功"
    else
        echo "❌ 前端應用啟動失敗"
        cat logs/frontend.log
        exit 1
    fi
}

# 顯示部署資訊
show_deployment_info() {
    echo ""
    echo "🎉 部署完成！"
    echo ""
    echo "📋 服務資訊："
    echo "  - 後端 API: http://localhost:8000"
    echo "  - API 文檔: http://localhost:8000/docs"
    echo "  - 前端應用: http://localhost:3000"
    echo ""
    echo "📊 系統狀態："
    echo "  - API PID: $(cat api.pid 2>/dev/null || echo '未知')"
    echo "  - Frontend PID: $(cat frontend.pid 2>/dev/null || echo '未知')"
    echo ""
    echo "📝 日誌檔案："
    echo "  - API 日誌: logs/api.log"
    echo "  - 前端日誌: logs/frontend.log"
    echo ""
    echo "⚠️  重要提醒："
    echo "  1. 請確保您的 Google Maps API 金鑰已正確設定"
    echo "  2. 請確保您的 TDX API 憑證已正確設定"
    echo "  3. 系統需要穩定的網路連接以取得即時交通資料"
    echo ""
    echo "🛑 停止服務："
    echo "  ./stop_services.sh"
}

# 建立停止服務腳本
create_stop_script() {
    cat > stop_services.sh << 'EOF'
#!/bin/bash

echo "🛑 停止交通衝擊波預測系統..."

# 停止 API 服務
if [ -f "api.pid" ]; then
    API_PID=$(cat api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        kill $API_PID
        echo "✅ 後端 API 已停止"
    fi
    rm api.pid
fi

# 停止前端服務
if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "✅ 前端應用已停止"
    fi
    rm frontend.pid
fi

echo "🎯 所有服務已停止"
EOF

    chmod +x stop_services.sh
}

# 主要部署流程
main() {
    check_requirements
    setup_environment
    create_directories
    install_backend_dependencies
    install_frontend_dependencies
    test_backend
    build_frontend
    create_stop_script
    start_services
    show_deployment_info
}

# 執行部署
main