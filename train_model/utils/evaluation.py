"""
RAG 系統評估工具
"""

import json
import asyncio
import numpy as np
from typing import List, Dict, Any, Tuple
from loguru import logger
from pathlib import Path

class RAGEvaluator:
    """RAG 系統評估器"""
    
    def __init__(self, rag_chat_system):
        """初始化評估器"""
        self.rag_chat = rag_chat_system
        self.evaluation_results = []
        
    def load_test_questions(self, test_file: str = None) -> List[Dict[str, Any]]:
        """載入測試問題"""
        if test_file is None:
            # 使用內建測試問題
            return self._get_default_test_questions()
        
        with open(test_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_default_test_questions(self) -> List[Dict[str, Any]]:
        """獲取預設測試問題"""
        return [
            {
                "id": "q1",
                "question": "國道一號的標準車道寬度是多少？",
                "category": "基礎設施",
                "expected_keywords": ["車道寬", "3.5", "3.6", "公尺"],
                "difficulty": "簡單"
            },
            {
                "id": "q2", 
                "question": "高速公路的縱向坡度設計有什麼限制？",
                "category": "工程設計",
                "expected_keywords": ["縱向坡度", "設計", "限制", "%"],
                "difficulty": "中等"
            },
            {
                "id": "q3",
                "question": "國道三號相比國道一號在路面設計上有什麼特色？",
                "category": "比較分析", 
                "expected_keywords": ["國道三號", "國道一號", "差異", "特色"],
                "difficulty": "困難"
            },
            {
                "id": "q4",
                "question": "什麼情況下會設置輔助車道？輔助車道的寬度標準是什麼？",
                "category": "專業知識",
                "expected_keywords": ["輔助車道", "設置", "寬度", "標準"],
                "difficulty": "中等"
            },
            {
                "id": "q5",
                "question": "高速公路曲率半徑的設計考量有哪些？",
                "category": "工程設計",
                "expected_keywords": ["曲率半徑", "設計", "安全", "速度"],
                "difficulty": "困難"
            }
        ]
    
    async def evaluate_single_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """評估單一問題"""
        question = question_data["question"]
        expected_keywords = question_data.get("expected_keywords", [])
        
        logger.info(f"評估問題: {question}")
        
        # 獲取回答
        try:
            answer = await self.rag_chat.chat(question)
            
            # 評估回答品質
            scores = self._evaluate_answer(answer, expected_keywords)
            
            result = {
                "question_id": question_data["id"],
                "question": question,
                "answer": answer,
                "category": question_data.get("category", "未分類"),
                "difficulty": question_data.get("difficulty", "未知"),
                "scores": scores,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"評估問題時發生錯誤: {e}")
            return {
                "question_id": question_data["id"],
                "question": question,
                "answer": f"錯誤: {str(e)}",
                "category": question_data.get("category", "未分類"),
                "difficulty": question_data.get("difficulty", "未知"),
                "scores": {"error": True},
                "timestamp": asyncio.get_event_loop().time()
            }
    
    def _evaluate_answer(self, answer: str, expected_keywords: List[str]) -> Dict[str, float]:
        """評估回答品質"""
        scores = {}
        
        # 1. 關鍵詞覆蓋率
        if expected_keywords:
            found_keywords = sum(1 for keyword in expected_keywords 
                               if keyword.lower() in answer.lower())
            scores["keyword_coverage"] = found_keywords / len(expected_keywords)
        else:
            scores["keyword_coverage"] = 0.0
        
        # 2. 回答長度評分（適中長度得分較高）
        answer_length = len(answer)
        if 50 <= answer_length <= 500:
            scores["length_score"] = 1.0
        elif answer_length < 50:
            scores["length_score"] = answer_length / 50
        else:
            scores["length_score"] = max(0.5, 1 - (answer_length - 500) / 1000)
        
        # 3. 資訊密度（根據標點符號和結構評估）
        sentences = len([s for s in answer.split('。') if s.strip()])
        if sentences > 0:
            avg_sentence_length = answer_length / sentences
            # 適中的句子長度得分較高
            if 20 <= avg_sentence_length <= 80:
                scores["info_density"] = 1.0
            else:
                scores["info_density"] = max(0.3, 1 - abs(avg_sentence_length - 50) / 100)
        else:
            scores["info_density"] = 0.0
        
        # 4. 專業術語使用（檢查是否包含相關術語）
        technical_terms = ["公尺", "車道", "坡度", "半徑", "設計", "標準", "國道", "高速公路"]
        found_terms = sum(1 for term in technical_terms if term in answer)
        scores["technical_score"] = min(1.0, found_terms / 5)  # 最多5個術語滿分
        
        # 5. 總體評分（加權平均）
        weights = {
            "keyword_coverage": 0.3,
            "length_score": 0.2, 
            "info_density": 0.2,
            "technical_score": 0.3
        }
        
        scores["overall_score"] = sum(scores[key] * weights[key] for key in weights)
        
        return scores
    
    async def run_full_evaluation(self, test_file: str = None) -> Dict[str, Any]:
        """執行完整評估"""
        logger.info("開始執行 RAG 系統完整評估...")
        
        # 載入測試問題
        test_questions = self.load_test_questions(test_file)
        logger.info(f"載入 {len(test_questions)} 個測試問題")
        
        # 清除聊天歷史以確保公平測試
        self.rag_chat.clear_history()
        
        # 評估每個問題
        results = []
        for i, question_data in enumerate(test_questions, 1):
            logger.info(f"評估進度: {i}/{len(test_questions)}")
            result = await self.evaluate_single_question(question_data)
            results.append(result)
            
            # 短暫延遲避免過於頻繁的請求
            await asyncio.sleep(2)
        
        # 計算統計結果
        stats = self._calculate_statistics(results)
        
        evaluation_report = {
            "evaluation_time": asyncio.get_event_loop().time(),
            "total_questions": len(test_questions),
            "results": results,
            "statistics": stats
        }
        
        self.evaluation_results.append(evaluation_report)
        logger.info("評估完成")
        
        return evaluation_report
    
    def _calculate_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算評估統計"""
        # 過濾出有效結果
        valid_results = [r for r in results if not r["scores"].get("error", False)]
        
        if not valid_results:
            return {"error": "沒有有效的評估結果"}
        
        # 提取各項評分
        scores = {
            "keyword_coverage": [r["scores"]["keyword_coverage"] for r in valid_results],
            "length_score": [r["scores"]["length_score"] for r in valid_results],
            "info_density": [r["scores"]["info_density"] for r in valid_results], 
            "technical_score": [r["scores"]["technical_score"] for r in valid_results],
            "overall_score": [r["scores"]["overall_score"] for r in valid_results]
        }
        
        # 計算統計指標
        stats = {}
        for score_type, values in scores.items():
            stats[score_type] = {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values),
                "median": np.median(values)
            }
        
        # 按難度分組統計
        difficulty_stats = {}
        for difficulty in ["簡單", "中等", "困難"]:
            difficulty_results = [r for r in valid_results if r["difficulty"] == difficulty]
            if difficulty_results:
                difficulty_scores = [r["scores"]["overall_score"] for r in difficulty_results]
                difficulty_stats[difficulty] = {
                    "count": len(difficulty_results),
                    "mean_score": np.mean(difficulty_scores)
                }
        
        stats["by_difficulty"] = difficulty_stats
        
        # 按類別分組統計
        category_stats = {}
        categories = set(r["category"] for r in valid_results)
        for category in categories:
            category_results = [r for r in valid_results if r["category"] == category]
            category_scores = [r["scores"]["overall_score"] for r in category_results]
            category_stats[category] = {
                "count": len(category_results),
                "mean_score": np.mean(category_scores)
            }
        
        stats["by_category"] = category_stats
        
        return stats
    
    def print_evaluation_report(self, report: Dict[str, Any]):
        """列印評估報告"""
        print("\n" + "="*60)
        print("🔍 RAG 系統評估報告")
        print("="*60)
        
        stats = report["statistics"]
        if "error" in stats:
            print(f"評估失敗: {stats['error']}")
            return
        
        # 總體統計
        overall = stats["overall_score"]
        print(f"總體評分: {overall['mean']:.3f} ± {overall['std']:.3f}")
        print(f"評分範圍: {overall['min']:.3f} - {overall['max']:.3f}")
        print(f"中位數: {overall['median']:.3f}")
        
        # 各項指標
        print(f"\n📊 詳細評分:")
        metrics = ["keyword_coverage", "length_score", "info_density", "technical_score"]
        metric_names = ["關鍵詞覆蓋率", "回答長度", "資訊密度", "專業術語"]
        
        for metric, name in zip(metrics, metric_names):
            score = stats[metric]["mean"]
            print(f"  {name}: {score:.3f}")
        
        # 按難度統計
        if "by_difficulty" in stats and stats["by_difficulty"]:
            print(f"\n📈 按難度分組:")
            for difficulty, data in stats["by_difficulty"].items():
                print(f"  {difficulty}: {data['mean_score']:.3f} ({data['count']} 題)")
        
        # 按類別統計
        if "by_category" in stats and stats["by_category"]:
            print(f"\n📂 按類別分組:")
            for category, data in stats["by_category"].items():
                print(f"  {category}: {data['mean_score']:.3f} ({data['count']} 題)")
        
        print("="*60)
    
    def save_evaluation_report(self, report: Dict[str, Any], output_file: str):
        """儲存評估報告"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"評估報告已儲存至: {output_file}")

if __name__ == "__main__":
    # 這裡可以添加獨立測試代碼
    print("RAG 評估工具模組")