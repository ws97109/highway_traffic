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
