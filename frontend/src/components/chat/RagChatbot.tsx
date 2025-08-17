'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';

interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: string[];
  confidence?: number;
  processingTime?: number;
}

interface RAGChatbotProps {
  isOpen: boolean;
  onClose: () => void;
  position?: 'fixed' | 'embedded';
  className?: string;
}

const RAGChatbot: React.FC<RAGChatbotProps> = ({ 
  isOpen, 
  onClose, 
  position = 'fixed',
  className = ''
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: '您好！我是高速公路智能助手，可以回答關於國道交通、路段規格、設計標準等問題。請問有什麼可以幫助您的嗎？',
      role: 'assistant',
      timestamp: new Date()
    }
  ]);
  
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  // 動態調整 textarea 高度
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 120; // 最大高度約3-4行
      textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputMessage]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputMessage.trim(),
      role: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const startTime = Date.now();
      
      const response = await fetch('/api/controller/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: 'control-center-' + Date.now(),
          priority: "normal"
        })
      });

      const endTime = Date.now();
      const processingTime = endTime - startTime;

      if (!response.ok) {
        throw new Error('網路請求失敗');
      }

      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: data.response || '抱歉，我現在無法回答這個問題。',
        role: 'assistant',
        timestamp: new Date(),
        sources: data.supporting_data || [],
        confidence: data.confidence_score || 0,
        processingTime: processingTime
      };

      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (error) {
      console.error('發送訊息失敗:', error);
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: '抱歉，發生了技術錯誤。請稍後再試，或檢查網路連接。',
        role: 'assistant',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        content: '對話已清除。我是高速公路智能助手，有什麼可以幫助您的嗎？',
        role: 'assistant',
        timestamp: new Date()
      }
    ]);
  };

  const suggestedQuestions = [
    "五股林口塞車問題可以怎麼解決？",
    "國道一號桃園段的車道配置多少是表現最佳的？",
    "八德到龍潭段有什麼交通特色？",
    "國道三號土城段的車道配置多少是表現最佳的？"
  ];

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-TW', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  if (!isOpen) return null;

  const containerClass = position === 'fixed' 
    ? 'fixed bottom-4 right-4 w-96 h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 z-50 flex flex-col'
    : `w-full h-full bg-white rounded-lg shadow border border-gray-200 flex flex-col ${className}`;

  return (
    <div className={containerClass}>
      {/* 聊天標題列 */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-t-lg flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <ChatBubbleLeftRightIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold">智能交通助手</h3>
              <p className="text-xs text-white/80">基於 RAG 技術驅動</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={clearChat}
              className="p-1 hover:bg-white/20 rounded"
              title="清除對話"
            >
              <ArrowPathIcon className="w-4 h-4" />
            </button>
            
            {position === 'fixed' && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded"
                title="關閉聊天"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 聊天訊息區域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="text-sm whitespace-pre-wrap">{message.content}</div>
              
              {/* 助手訊息的額外資訊 */}
              {message.role === 'assistant' && (
                <div className="mt-2 space-y-2">
                  {/* 信心度指標 */}
                  {message.confidence !== undefined && (
                    <div className="flex items-center space-x-2 text-xs">
                      <span className="text-gray-500">準確度:</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(message.confidence)}`}>
                        {(message.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  
                  {/* 資料來源 */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="text-xs text-gray-500">
                      <div className="flex items-center space-x-1 mb-1">
                        <DocumentTextIcon className="w-3 h-3" />
                        <span>參考資料:</span>
                      </div>
                      <div className="pl-4 space-y-1">
                        {message.sources.slice(0, 3).map((source, index) => (
                          <div key={index} className="text-gray-600">
                            • {source.length > 60 ? source.substring(0, 60) + '...' : source}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* 處理時間 */}
                  {message.processingTime && (
                    <div className="flex items-center space-x-1 text-xs text-gray-500">
                      <ClockIcon className="w-3 h-3" />
                      <span>處理時間: {message.processingTime}ms</span>
                    </div>
                  )}
                </div>
              )}
              
              <div className={`text-xs mt-2 ${
                message.role === 'user' ? 'text-white/70' : 'text-gray-500'
              }`}>
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ))}
        
        {/* 載入指示器 */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-xs text-gray-500">正在思考中...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 建議問題 */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex-shrink-0">
          <div className="text-xs text-gray-500 mb-2">建議問題:</div>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => setInputMessage(question)}
                className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded hover:bg-blue-100 transition-colors"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 改進的輸入區域 */}
      <div className="border-t border-gray-200 p-3 flex-shrink-0">
        <div className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="輸入您的問題..."
              disabled={isLoading}
              rows={1}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 overflow-hidden"
              style={{ minHeight: '38px', maxHeight: '120px' }}
            />
          </div>
          
          <button
            onClick={sendMessage}
            disabled={isLoading || !inputMessage.trim()}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            {isLoading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RAGChatbot;