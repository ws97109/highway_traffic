#!/usr/bin/env node

/**
 * Ollama API 測試腳本
 * 用於診斷 Next.js API Route 與 Ollama 的連接問題
 */

const fetch = require('node-fetch');

const OLLAMA_URL = 'http://localhost:11434';
const NEXT_API_URL = 'http://localhost:3000';

async function testOllamaDirectly() {
  console.log('\n🔵 測試 1: 直接連接 Ollama 服務');
  console.log('URL:', OLLAMA_URL);

  try {
    // 測試 /api/tags
    const tagsResponse = await fetch(`${OLLAMA_URL}/api/tags`);
    if (tagsResponse.ok) {
      const data = await tagsResponse.json();
      console.log('✅ Ollama 服務正常');
      console.log('可用模型:', data.models.map(m => m.name).join(', '));

      // 測試 /api/generate
      console.log('\n測試生成回應...');
      const generateResponse = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'qwen2.5:7b',
          prompt: '你好，請簡單回答',
          stream: false
        })
      });

      if (generateResponse.ok) {
        const result = await generateResponse.json();
        console.log('✅ 生成測試成功');
        console.log('回應:', result.response.substring(0, 100) + '...');
      } else {
        console.error('❌ 生成測試失敗:', generateResponse.status);
      }
    } else {
      console.error('❌ Ollama 服務無回應:', tagsResponse.status);
    }
  } catch (error) {
    console.error('❌ 連接 Ollama 失敗:', error.message);
  }
}

async function testNextAPI() {
  console.log('\n🔵 測試 2: Next.js API Route');
  console.log('URL:', `${NEXT_API_URL}/api/rag/chat`);

  try {
    // 測試 GET (健康檢查)
    const healthResponse = await fetch(`${NEXT_API_URL}/api/rag/chat`);
    if (healthResponse.ok) {
      const data = await healthResponse.json();
      console.log('✅ API 健康檢查成功');
      console.log('狀態:', data.status);
    } else {
      console.error('❌ API 健康檢查失敗:', healthResponse.status);
      const errorText = await healthResponse.text();
      console.error('錯誤:', errorText);
    }

    // 測試 POST (對話)
    console.log('\n測試 POST 請求...');
    const chatResponse = await fetch(`${NEXT_API_URL}/api/rag/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: '你好，請簡單回答',
        user_location: { lat: 25.0330, lng: 121.5654 }
      })
    });

    if (chatResponse.ok) {
      const data = await chatResponse.json();
      console.log('✅ API 對話測試成功');
      console.log('回應:', data.response.substring(0, 100) + '...');
    } else {
      console.error('❌ API 對話測試失敗:', chatResponse.status);
      const errorData = await chatResponse.json();
      console.error('錯誤:', JSON.stringify(errorData, null, 2));
    }
  } catch (error) {
    console.error('❌ 連接 Next.js API 失敗:', error.message);
    console.error('請確認開發伺服器是否在運行 (npm run dev)');
  }
}

async function main() {
  console.log('═══════════════════════════════════════');
  console.log('  Ollama API 診斷工具');
  console.log('═══════════════════════════════════════');

  await testOllamaDirectly();
  await testNextAPI();

  console.log('\n═══════════════════════════════════════');
  console.log('  診斷完成');
  console.log('═══════════════════════════════════════\n');
}

main().catch(console.error);
