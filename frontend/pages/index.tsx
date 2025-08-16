'use client';

import { useRouter } from 'next/router'
import { useState, useEffect } from 'react'
import { 
  MapIcon, 
  ChartBarIcon, 
  ExclamationTriangleIcon,
  UserIcon,
  CogIcon,
  ArrowRightIcon,
  BoltIcon,
  ClockIcon,
  SignalIcon
} from '@heroicons/react/24/outline'

export default function Home() {
  const router = useRouter()
  const [currentTime, setCurrentTime] = useState<Date | null>(null)
  const [systemStats, setSystemStats] = useState({
    activeUsers: 1247,
    monitoringStations: 62,
    activeAlerts: 3,
    systemUptime: '99.8%'
  })

  useEffect(() => {
    // 初始化時間，避免 hydration 錯誤
    setCurrentTime(new Date())
    
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const navigateToDriver = () => {
    router.push('/driver')
  }

  const navigateToAdmin = () => {
    router.push('/admin')
  }

  const features = [
    {
      icon: MapIcon,
      title: '即時交通監控',
      description: '全台高速公路即時交通狀況監控與分析',
      color: 'text-blue-600 bg-blue-100'
    },
    {
      icon: BoltIcon,
      title: '震波預警系統',
      description: '智慧偵測交通震波，提前預警避免事故',
      color: 'text-purple-600 bg-purple-100'
    },
    {
      icon: ChartBarIcon,
      title: 'AI 預測分析',
      description: '運用機器學習預測交通流量與壅塞狀況',
      color: 'text-green-600 bg-green-100'
    },
    {
      icon: SignalIcon,
      title: '智慧路線規劃',
      description: '動態路線最佳化，節省時間與燃料成本',
      color: 'text-orange-600 bg-orange-100'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* 頂部導航 */}
      <nav className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <BoltIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">智慧交通系統</h1>
                <p className="text-xs text-gray-500">Highway Traffic Intelligence</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                {currentTime ? currentTime.toLocaleString('zh-TW', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                }) : '載入中...'}
              </div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要內容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        
        {/* 歡迎區塊 */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            高速公路智慧交通
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              預警決策支援系統
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            運用人工智慧與大數據分析，提供即時交通監控、震波預警與智慧決策支援，
            讓每一次出行都更安全、更順暢。
          </p>
        </div>

        {/* 用戶選擇區塊 */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          
          {/* 駕駛者入口 */}
          <div 
            onClick={navigateToDriver}
            className="group bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-gray-200/50 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer hover:scale-105"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <UserIcon className="w-8 h-8 text-white" />
              </div>
              <ArrowRightIcon className="w-6 h-6 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900 mb-3">駕駛者介面</h2>
            <p className="text-gray-600 mb-6">
              獲取即時交通資訊、路線規劃建議與震波預警通知，
              讓您的每次出行都能避開壅塞，安全抵達目的地。
            </p>
            
            <div className="space-y-2">
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
                即時路況與導航
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
                震波預警通知
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
                智慧出發時間建議
              </div>
            </div>
          </div>

          {/* 管理員入口 */}
          <div 
            onClick={navigateToAdmin}
            className="group bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-gray-200/50 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer hover:scale-105"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CogIcon className="w-8 h-8 text-white" />
              </div>
              <ArrowRightIcon className="w-6 h-6 text-gray-400 group-hover:text-purple-600 group-hover:translate-x-1 transition-all" />
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900 mb-3">管理控制中心</h2>
            <p className="text-gray-600 mb-6">
              全面監控高速公路交通狀況，管理預警系統，
              執行AI決策建議，確保交通系統高效運作。
            </p>
            
            <div className="space-y-2">
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
                系統監控與管理
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
                AI決策支援系統
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
                交通流量分析
              </div>
            </div>
          </div>
        </div>

        {/* 系統特色 */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">系統核心功能</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div key={index} className="bg-white/60 backdrop-blur-sm rounded-xl p-6 border border-gray-200/50 shadow-sm hover:shadow-md transition-shadow">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 ${feature.color}`}>
                  <feature.icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 即時狀態指示器 */}
        <div className="bg-white/60 backdrop-blur-sm rounded-xl p-6 border border-gray-200/50 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-gray-700">系統運行正常</span>
              </div>
              <div className="text-sm text-gray-500">
                最後更新: {currentTime ? currentTime.toLocaleTimeString('zh-TW') : '載入中...'}
              </div>
            </div>
            
            <div className="flex items-center space-x-6 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <ClockIcon className="w-4 h-4" />
                <span>24/7 監控</span>
              </div>
              <div className="flex items-center space-x-2">
                <ExclamationTriangleIcon className="w-4 h-4" />
                <span>即時預警</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 頁腳 */}
      <footer className="bg-white/50 backdrop-blur-sm border-t border-gray-200/50 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600">
            <p className="text-sm">
              © 2024 高速公路智慧交通預警決策支援系統 - 讓每一次出行都更安全
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
