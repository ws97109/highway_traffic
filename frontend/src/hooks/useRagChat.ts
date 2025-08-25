// frontend/src/hooks/useRAGChat.ts
import { useState, useCallback } from 'react';

interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: string[];
  confidence?: number;
  processingTime?: number;
}

interface RAGResponse {
  response: string;
  sources?: string[];
  confidence?: number;
  conversation_id?: string;
  retrieval_info?: {
    document_count: number;
    search_time: number;
  };
}

interface UseRAGChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  isConnected: boolean;
}

export const useRAGChat = (): UseRAGChatReturn => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: '您好！我是高速公路智能助手，可以回答關於國道交通、路段規格、設計標準等問題。請問有什麼可以幫助您的嗎？',
      role: 'assistant',
      timestamp: new Date()
    }
  ]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(true);

  const sendMessage = useCallback(async (messageContent: string) => {
    if (!messageContent.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: messageContent.trim(),
      role: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const startTime = Date.now();
      
      // 調用後端 RAG API
      const response = await fetch('/api/chat/rag', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageContent.trim(),
          conversation_id: 'web-chat-' + Date.now(),
          include_sources: true,
          max_tokens: 500
        })
      });

      const endTime = Date.now();
      const processingTime = endTime - startTime;

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: RAGResponse = await response.json();
      setIsConnected(true);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: data.response || '抱歉，我現在無法回答這個問題。',
        role: 'assistant',
        timestamp: new Date(),
        sources: data.sources || [],
        confidence: data.confidence || 0,
        processingTime: processingTime
      };

      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (error) {
      console.error('發送訊息失敗:', error);
      setIsConnected(false);
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: '抱歉，發生了技術錯誤。請稍後再試，或檢查網路連接。如果問題持續，請聯繫系統管理員。',
        role: 'assistant',
        timestamp: new Date(),
        confidence: 0
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([
      {
        id: '1',
        content: '對話已清除。我是高速公路智能助手，有什麼可以幫助您的嗎？',
        role: 'assistant',
        timestamp: new Date()
      }
    ]);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    clearMessages,
    isConnected
  };
};