#!/usr/bin/env python3
"""
測試 RAG 系統
驗證 RAG API 是否正確運作並使用繁體中文回答
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_rag_status():
    """測試 RAG 系統狀態"""
    print("=" * 60)
    print("📊 測試 RAG 系統狀態")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE}/api/rag/status", timeout=5)
        if response.ok:
            data = response.json()
            print("✅ RAG 系統狀態：", data.get('status'))
            print(f"📚 知識庫文件數：{data.get('knowledge_base_documents')}")
            print(f"🤖 Ollama 連接：{data.get('ollama_connected')}")
            print(f"✨ RAG 啟用：{data.get('rag_enabled')}")
            print(f"🇹🇼 繁體中文支援：{data.get('features', {}).get('traditional_chinese')}")
            return True
        else:
            print(f"❌ RAG 系統狀態檢查失敗：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 無法連接到 RAG 系統：{e}")
        return False

def test_knowledge_base():
    """測試知識庫"""
    print("\n" + "=" * 60)
    print("📚 測試知識庫")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE}/api/rag/knowledge-base", timeout=5)
        if response.ok:
            data = response.json()
            print(f"✅ 知識庫文件總數：{data.get('total_documents')}")
            print(f"📑 知識類別：{', '.join(data.get('categories', []))}")

            # 顯示前 3 個文件的標題
            documents = data.get('documents', [])
            if documents:
                print("\n📄 知識庫範例文件：")
                for i, doc in enumerate(documents[:3], 1):
                    print(f"{i}. [{doc.get('category')}] {doc.get('id')}")
                    print(f"   內容：{doc.get('content')[:60]}...")
            return True
        else:
            print(f"❌ 知識庫查詢失敗：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 知識庫查詢錯誤：{e}")
        return False

def test_knowledge_search():
    """測試知識庫搜尋"""
    print("\n" + "=" * 60)
    print("🔍 測試知識庫搜尋")
    print("=" * 60)

    test_queries = [
        "五股林口壅塞",
        "休息站",
        "國道一號"
    ]

    for query in test_queries:
        print(f"\n🔎 搜尋：「{query}」")
        try:
            response = requests.post(
                f"{API_BASE}/api/rag/search-knowledge",
                params={"query": query, "top_k": 2},
                timeout=5
            )
            if response.ok:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ 找到 {len(results)} 個相關文件")
                for i, result in enumerate(results, 1):
                    print(f"{i}. [{result.get('category')}]")
                    print(f"   {result.get('content')[:80]}...")
            else:
                print(f"❌ 搜尋失敗：{response.status_code}")
        except Exception as e:
            print(f"❌ 搜尋錯誤：{e}")

def test_rag_chat():
    """測試 RAG 對話（最重要的測試）"""
    print("\n" + "=" * 60)
    print("💬 測試 RAG 對話功能")
    print("=" * 60)

    test_questions = [
        {
            "message": "五股林口塞車問題可以怎麼解決？",
            "description": "測試交通問題回答"
        },
        {
            "message": "國道一號有哪些休息站？",
            "description": "測試知識庫檢索"
        },
        {
            "message": "遇到交通震波應該怎麼辦？",
            "description": "測試震波知識"
        }
    ]

    for i, test in enumerate(test_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"測試 {i}：{test['description']}")
        print(f"問題：{test['message']}")
        print(f"{'─' * 60}")

        try:
            response = requests.post(
                f"{API_BASE}/api/rag/chat",
                json={
                    "message": test['message'],
                    "use_rag": True,
                    "traffic_data": None,
                    "shockwave_data": None,
                    "user_location": None
                },
                timeout=30
            )

            if response.ok:
                data = response.json()
                print(f"\n✅ AI 回應（信心度：{data.get('confidence_score', 0):.2f}）：")
                print(f"{data.get('response', '無回應')}")

                # 檢查是否使用繁體中文
                response_text = data.get('response', '')
                has_simplified = any(char in response_text for char in ['车', '线', '为', '国', '时'])
                if has_simplified:
                    print("\n⚠️ 警告：回應可能包含簡體字！")
                else:
                    print("\n✅ 確認：使用繁體中文")

                # 顯示 RAG 來源
                sources = data.get('sources', [])
                if sources:
                    print(f"\n📚 RAG 檢索到 {len(sources)} 個相關知識：")
                    for j, source in enumerate(sources, 1):
                        print(f"{j}. {source[:60]}...")
                else:
                    print("\n⚠️ 沒有使用 RAG 知識庫")

                print(f"\n🤖 模型：{data.get('model')}")
                print(f"⏰ 時間戳記：{data.get('timestamp')}")
            else:
                print(f"❌ 對話失敗：HTTP {response.status_code}")
                print(f"錯誤訊息：{response.text}")
        except requests.exceptions.Timeout:
            print("❌ 請求超時（30秒），請檢查 Ollama 服務是否運行")
        except Exception as e:
            print(f"❌ 對話錯誤：{e}")

def test_traditional_chinese_conversion():
    """測試繁體中文轉換"""
    print("\n" + "=" * 60)
    print("🇹🇼 測試繁體中文轉換功能")
    print("=" * 60)

    # 測試包含簡體字的問題
    response = requests.post(
        f"{API_BASE}/api/rag/chat",
        json={
            "message": "请问国道一号的车流状况如何？",  # 故意使用簡體中文
            "use_rag": True,
            "traffic_data": None,
            "shockwave_data": None,
            "user_location": None
        },
        timeout=30
    )

    if response.ok:
        data = response.json()
        response_text = data.get('response', '')

        print(f"✅ AI 回應：\n{response_text}\n")

        # 檢查簡體字
        simplified_chars = ['车', '线', '为', '国', '时', '应', '间', '发']
        found_simplified = [char for char in simplified_chars if char in response_text]

        if found_simplified:
            print(f"⚠️ 發現簡體字：{', '.join(found_simplified)}")
            print("❌ 繁體中文轉換可能需要改進")
        else:
            print("✅ 確認：回應完全使用繁體中文")
    else:
        print(f"❌ 測試失敗：{response.status_code}")

def main():
    """主測試函數"""
    print("\n" + "🚀" * 30)
    print(" " * 15 + "RAG 系統完整測試")
    print("🚀" * 30 + "\n")

    # 執行所有測試
    tests = [
        ("系統狀態", test_rag_status),
        ("知識庫", test_knowledge_base),
        ("知識搜尋", test_knowledge_search),
        ("RAG 對話", test_rag_chat),
        ("繁體中文", test_traditional_chinese_conversion)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 測試發生錯誤：{e}")
            results.append((test_name, False))

    # 總結
    print("\n" + "=" * 60)
    print("📊 測試總結")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:20s} : {status}")

    print(f"\n總計：{passed}/{total} 個測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！RAG 系統運作正常！")
    else:
        print(f"\n⚠️ {total - passed} 個測試失敗，請檢查錯誤訊息")

if __name__ == "__main__":
    main()
