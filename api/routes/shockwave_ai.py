from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
import math
from datetime import datetime, timedelta
import os
import re

router = APIRouter()

# Ollama 設定
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')

# 簡繁轉換對照表 (包含交通相關常用詞彙)
SIMPLIFIED_TO_TRADITIONAL = {
    '简': '簡', '体': '體', '还': '還', '这': '這', '为': '為', '预': '預',
    '车': '車', '图': '圖', '种': '種', '应': '應', '处': '處', '过': '過',
    '时': '時', '没': '沒', '现': '現', '国': '國', '经': '經', '观': '觀',
    '变': '變', '学': '學', '开': '開', '关': '關', '门': '門', '间': '間',
    '发': '發', '长': '長', '当': '當', '导': '導', '评': '評', '话': '話',
    '说': '說', '听': '聽', '写': '寫', '读': '讀', '认': '認', '议': '議',
    '问': '問', '题': '題', '难': '難', '验': '驗', '历': '歷', '业': '業',
    '产': '產', '务': '務', '价': '價', '值': '值', '质': '質', '量': '量',
    '项': '項', '级': '級', '线': '線', '线路': '線路', '检': '檢', '测': '測',
    '终': '終', '给': '給', '带': '帶', '来': '來', '许': '許', '赶': '趕',
    '紧': '緊', '紧急': '緊急', '关键': '關鍵', '进': '進', '远': '遠',
    '运': '運', '转': '轉', '传': '傳', '播': '播', '响': '響', '影响': '影響',
    '范': '範', '围': '圍', '范围': '範圍', '选': '選', '择': '擇', '选择': '選擇',
    '环': '環', '境': '境', '环境': '環境', '联': '聯', '系': '系', '联系': '聯繫',
    '结': '結', '果': '果', '结果': '結果', '标': '標', '准': '準', '标准': '標準',
    '确': '確', '实': '實', '确实': '確實', '记': '記', '录': '錄', '记录': '記錄',
    '资': '資', '料': '料', '资料': '資料', '较': '較', '获': '獲', '取': '取',
    '获取': '獲取', '处理': '處理', '设': '設', '置': '置', '设置': '設置',
    '场': '場', '景': '景', '场景': '場景', '显': '顯', '示': '示', '显示': '顯示',
    '内': '內', '容': '容', '内容': '內容', '态': '態', '状态': '狀態',
    '位': '位', '置': '置', '位置': '位置', '计': '計', '算': '算', '计算': '計算',
    '继': '繼', '续': '續', '继续': '繼續', '维': '維', '护': '護', '维护': '維護',
    '总': '總', '结': '結', '总结': '總結', '压': '壓', '力': '力', '压力': '壓力',
    '优': '優', '化': '化', '优化': '優化', '灾': '災', '害': '害', '灾害': '災害',
    '紧急情况': '緊急情況', '紧急': '緊急', '复': '復', '杂': '雜', '复杂': '複雜',
    '节': '節', '省': '省', '节省': '節省', '满': '滿', '足': '足', '满足': '滿足',
    '达': '達', '到': '到', '达到': '達到', '活': '活', '动': '動', '活动': '活動',
    '增': '增', '加': '加', '增加': '增加', '减': '減', '少': '少', '减少': '減少',
    '降': '降', '低': '低', '降低': '降低', '提': '提', '高': '高', '提高': '提高',
    '强': '強', '度': '度', '强度': '強度', '扩': '擴', '大': '大', '扩大': '擴大',
    '缩': '縮', '小': '小', '缩小': '縮小', '规': '規', '模': '模', '规模': '規模',
    '区': '區', '域': '域', '区域': '區域', '范围': '範圍', '路线': '路線',
    '线路': '線路', '轨': '軌', '道': '道', '轨道': '軌道', '铁': '鐵', '路': '路',
    '铁路': '鐵路', '公': '公', '路': '路', '公路': '公路', '高': '高', '速': '速',
    '高速': '高速', '快': '快', '速': '速', '快速': '快速', '慢': '慢', '行': '行',
    '慢行': '慢行', '停': '停', '车': '車', '停车': '停車', '避': '避', '免': '免',
    '避免': '避免', '禁': '禁', '止': '止', '禁止': '禁止', '限': '限', '制': '制',
    '限制': '限制', '严': '嚴', '重': '重', '严重': '嚴重', '轻': '輕', '微': '微',
    '轻微': '輕微', '危': '危', '险': '險', '危险': '危險', '安': '安', '全': '全',
    '安全': '安全', '注': '注', '意': '意', '注意': '注意', '建': '建', '议': '議',
    '建议': '建議', '方': '方', '案': '案', '方案': '方案', '措': '措', '施': '施',
    '措施': '措施', '应该': '應該', '需要': '需要', '可以': '可以', '能够': '能夠',
    '必须': '必須', '必要': '必要', '足够': '足夠', '适合': '適合', '合适': '合適',
    '尽量': '盡量', '尽快': '儘快', '及时': '及時', '立即': '立即', '马上': '馬上',
    '尽': '盡', '快': '快', '儘': '儘', '快': '快', '儘快': '儘快',
    '临': '臨', '时': '時', '临时': '臨時', '暂': '暫', '时': '時', '暂时': '暫時',
    '维': '維', '持': '持', '维持': '維持', '保': '保', '持': '持', '保持': '保持',
    '调': '調', '整': '整', '调整': '調整', '修': '修', '改': '改', '修改': '修改',
    '更': '更', '新': '新', '更新': '更新', '升': '升', '级': '級', '升级': '升級',
    '检查': '檢查', '监': '監', '控': '控', '监控': '監控', '观察': '觀察',
    '跟': '跟', '踪': '蹤', '跟踪': '跟蹤', '追': '追', '踪': '蹤', '追踪': '追蹤',
    '分': '分', '析': '析', '分析': '分析', '评': '評', '估': '估', '评估': '評估',
    '预': '預', '测': '測', '预测': '預測', '预': '預', '期': '期', '预期': '預期',
    '预': '預', '防': '防', '预防': '預防', '预': '預', '警': '警', '预警': '預警',
    '报': '報', '告': '告', '报告': '報告', '消': '消', '息': '息', '消息': '消息',
    '信': '信', '息': '息', '信息': '信息', '通': '通', '知': '知', '通知': '通知',
    '提': '提', '醒': '醒', '提醒': '提醒', '警': '警', '告': '告', '警告': '警告',
    '况': '況', '情况': '情況', '状': '狀', '况': '況', '状况': '狀況',
    '让': '讓', '令': '令', '使': '使', '得': '得', '到达': '到達',
    '离开': '離開', '进入': '進入', '退出': '退出', '通过': '通過',
    '经过': '經過', '穿过': '穿過', '越过': '越過', '跨越': '跨越',
    '返回': '返回', '回来': '回來', '前往': '前往', '驶向': '駛向',
    '驶入': '駛入', '驶出': '駛出', '驶过': '駛過', '行驶': '行駛',
    '行进': '行進', '前进': '前進', '后退': '後退', '倒车': '倒車',
    '掉头': '掉頭', '转弯': '轉彎', '拐弯': '拐彎', '变道': '變道',
    '换道': '換道', '超车': '超車', '并道': '並道', '合流': '合流',
    '分流': '分流', '汇入': '匯入', '汇合': '匯合', '会合': '會合',
    '集中': '集中', '分散': '分散', '聚集': '聚集', '散开': '散開',
    '拥堵': '擁堵', '堵塞': '堵塞', '阻塞': '阻塞', '畅通': '暢通',
    '缓慢': '緩慢', '顺畅': '順暢', '流畅': '流暢', '平稳': '平穩',
    '稳定': '穩定', '不稳': '不穩', '波动': '波動', '震荡': '震盪',
    '剧烈': '劇烈', '温和': '溫和', '轻微': '輕微', '严重': '嚴重',
    '紧急': '緊急', '紧急情况': '緊急情況', '紧急制动': '緊急制動',
    '急刹': '急剎', '急停': '急停', '紧急停车': '緊急停車',
    '紧急避让': '緊急避讓', '紧急疏散': '緊急疏散',
    '交通': '交通', '车辆': '車輛', '车流': '車流', '车速': '車速',
    '车道': '車道', '车距': '車距', '跟车': '跟車', '距离': '距離',
    '间距': '間距', '间隔': '間隔', '时间': '時間', '时刻': '時刻',
    '时段': '時段', '时期': '時期', '延时': '延時', '延迟': '延遲',
    '延误': '延誤', '提前': '提前', '准时': '準時', '及时': '及時',
    '实时': '即時', '即时': '即時', '同时': '同時', '当时': '當時',
    '临时': '臨時', '暂时': '暫時', '长时间': '長時間',
    '短时间': '短時間', '瞬间': '瞬間', '持续': '持續',
    '连续': '連續', '间断': '間斷', '中断': '中斷', '停止': '停止',
    '终止': '終止', '结束': '結束', '开始': '開始', '启动': '啟動',
    '开启': '開啟', '关闭': '關閉', '关上': '關上', '打开': '打開',
    '开放': '開放', '封闭': '封閉', '封锁': '封鎖', '解封': '解封',
    '解除': '解除', '取消': '取消', '暂停': '暫停', '恢复': '恢復',
    '重新': '重新', '再次': '再次', '重复': '重複', '反复': '反複',
    '多次': '多次', '频繁': '頻繁', '经常': '經常', '常常': '常常',
    '偶尔': '偶爾', '偶然': '偶然', '突然': '突然', '忽然': '忽然',
    '渐渐': '漸漸', '逐渐': '逐漸', '慢慢': '慢慢', '快速': '快速',
    '迅速': '迅速', '立刻': '立刻', '马上': '馬上', '立即': '立即',
    '赶紧': '趕緊', '赶快': '趕快', '快点': '快點', '抓紧': '抓緊',
    '尽快': '儘快', '尽早': '儘早', '尽量': '盡量', '努力': '努力',
    '试图': '試圖', '尝试': '嘗試', '企图': '企圖', '打算': '打算',
    '计划': '計劃', '准备': '準備', '安排': '安排', '组织': '組織',
    '协调': '協調', '配合': '配合', '合作': '合作', '联合': '聯合',
    '统一': '統一', '统筹': '統籌', '整合': '整合', '综合': '綜合',
    '全面': '全面', '整体': '整體', '局部': '局部', '部分': '部分',
    '个别': '個別', '单独': '單獨', '独立': '獨立', '分别': '分別',
    '各自': '各自', '共同': '共同', '一起': '一起', '同时': '同時',
    '齐心': '齊心', '团结': '團結', '协作': '協作', '配合': '配合',
    '沟通': '溝通', '联系': '聯繫', '联络': '聯絡', '联通': '聯通',
    '连接': '連接', '连通': '連通', '接通': '接通', '畅通': '暢通',
    '通讯': '通訊', '通信': '通信', '传达': '傳達', '传递': '傳遞',
    '传送': '傳送', '传输': '傳輸', '输送': '輸送', '运输': '運輸',
    '运送': '運送', '载运': '載運', '装载': '裝載', '装运': '裝運',
    '卸载': '卸載', '卸货': '卸貨', '装货': '裝貨', '货物': '貨物',
    '货车': '貨車', '客车': '客車', '轿车': '轎車', '汽车': '汽車',
    '机动车': '機動車', '非机动车': '非機動車',
    '摩托车': '摩托車', '自行车': '自行車', '电动车': '電動車',
    '公交车': '公交車', '巴士': '巴士', '出租车': '出租車',
    '救护车': '救護車', '消防车': '消防車', '警车': '警車',
    '工程车': '工程車', '拖车': '拖車', '挂车': '掛車',
    '半挂车': '半掛車', '全挂车': '全掛車',
    '标志': '標誌', '标识': '標識', '标记': '標記', '标示': '標示',
    '指示': '指示', '指引': '指引', '导向': '導向', '引导': '引導',
    '向导': '嚮導', '导航': '導航', '导向': '導向', '方向': '方向',
    '朝向': '朝向', '面向': '面向', '趋向': '趨向', '倾向': '傾向',
    '偏向': '偏向', '偏移': '偏移', '偏离': '偏離', '脱离': '脫離',
    '离开': '離開', '远离': '遠離', '靠近': '靠近', '接近': '接近',
    '临近': '臨近', '邻近': '鄰近', '附近': '附近', '周围': '周圍',
    '周边': '周邊', '四周': '四周', '环绕': '環繞', '围绕': '圍繞',
    '包围': '包圍', '环抱': '環抱', '拥抱': '擁抱', '怀抱': '懷抱',
    '依靠': '依靠', '依赖': '依賴', '依托': '依托', '凭借': '憑藉',
    '借助': '借助', '利用': '利用', '使用': '使用', '运用': '運用',
    '采用': '採用', '选用': '選用', '应用': '應用', '启用': '啟用',
    '弃用': '棄用', '停用': '停用', '废用': '廢用', '禁用': '禁用',
    '限用': '限用', '专用': '專用', '共用': '共用', '通用': '通用',
    '万用': '萬用', '多用': '多用', '单用': '單用', '独用': '獨用',
    '滥用': '濫用', '误用': '誤用', '错用': '錯用', '乱用': '亂用',
    '善用': '善用', '活用': '活用', '巧用': '巧用', '妙用': '妙用',
    '实用': '實用', '有用': '有用', '无用': '無用', '可用': '可用',
    '不可用': '不可用', '适用': '適用', '不适用': '不適用',
    '管': '管', '理': '理', '管理': '管理', '治': '治', '理': '理',
    '治理': '治理', '整': '整', '治': '治', '整治': '整治',
    '维': '維', '修': '修', '维修': '維修', '保': '保', '养': '養',
    '保养': '保養', '维': '維', '护': '護', '维护': '維護',
    '检': '檢', '修': '修', '检修': '檢修', '检': '檢', '查': '查',
    '检查': '檢查', '检': '檢', '验': '驗', '检验': '檢驗',
    '检': '檢', '测': '測', '检测': '檢測', '监': '監', '测': '測',
    '监测': '監測', '监': '監', '控': '控', '监控': '監控',
    '监': '監', '督': '督', '监督': '監督', '监': '監', '视': '視',
    '监视': '監視', '观': '觀', '察': '察', '观察': '觀察',
    '观': '觀', '测': '測', '观测': '觀測', '观': '觀', '看': '看',
    '观看': '觀看', '观': '觀', '赏': '賞', '观赏': '觀賞',
    '欣': '欣', '赏': '賞', '欣赏': '欣賞', '赞': '讚', '赏': '賞',
    '赞赏': '讚賞', '称': '稱', '赞': '讚', '称赞': '稱讚',
    '表': '表', '扬': '揚', '表扬': '表揚', '夸': '誇', '奖': '獎',
    '夸奖': '誇獎', '奖': '獎', '励': '勵', '奖励': '獎勵',
    '鼓': '鼓', '励': '勵', '鼓励': '鼓勵', '激': '激', '励': '勵',
    '激励': '激勵', '启': '啟', '发': '發', '启发': '啟發',
    '触': '觸', '发': '發', '触发': '觸發', '引': '引', '发': '發',
    '引发': '引發', '导': '導', '致': '致', '导致': '導致',
    '造': '造', '成': '成', '造成': '造成', '形': '形', '成': '成',
    '形成': '形成', '产': '產', '生': '生', '产生': '產生',
    '发': '發', '生': '生', '发生': '發生', '出': '出', '现': '現',
    '出现': '出現', '显': '顯', '现': '現', '显现': '顯現',
    '体': '體', '现': '現', '体现': '體現', '表': '表', '现': '現',
    '表现': '表現', '反': '反', '映': '映', '反映': '反映',
    '映': '映', '射': '射', '映射': '映射', '投': '投', '射': '射',
    '投射': '投射', '折': '折', '射': '射', '折射': '折射',
    '反': '反', '射': '射', '反射': '反射', '散': '散', '射': '射',
    '散射': '散射', '辐': '輻', '射': '射', '辐射': '輻射',
    '扩': '擴', '散': '散', '扩散': '擴散', '传': '傳', '播': '播',
    '传播': '傳播', '传': '傳', '递': '遞', '传递': '傳遞',
    '传': '傳', '导': '導', '传导': '傳導', '传': '傳', '输': '輸',
    '传输': '傳輸', '运': '運', '输': '輸', '运输': '運輸',
    '输': '輸', '送': '送', '输送': '輸送', '输': '輸', '出': '出',
    '输出': '輸出', '输': '輸', '入': '入', '输入': '輸入',
    '进': '進', '入': '入', '进入': '進入', '进': '進', '出': '出',
    '进出': '進出', '出': '出', '入': '入', '出入': '出入',
    '进': '進', '口': '口', '进口': '進口', '出': '出', '口': '口',
    '出口': '出口', '入': '入', '口': '口', '入口': '入口',
    '交': '交', '叉': '叉', '交叉': '交叉', '交': '交', '汇': '匯',
    '交汇': '交匯', '汇': '匯', '合': '合', '汇合': '匯合',
    '会': '會', '合': '合', '会合': '會合', '集': '集', '合': '合',
    '集合': '集合', '聚': '聚', '合': '合', '聚合': '聚合',
    '结': '結', '合': '合', '结合': '結合', '融': '融', '合': '合',
    '融合': '融合', '整': '整', '合': '合', '整合': '整合',
    '合': '合', '并': '併', '合并': '合併', '并': '併', '入': '入',
    '并入': '併入', '归': '歸', '并': '併', '归并': '歸併',
    '分': '分', '离': '離', '分离': '分離', '分': '分', '开': '開',
    '分开': '分開', '分': '分', '割': '割', '分割': '分割',
    '分': '分', '解': '解', '分解': '分解', '拆': '拆', '分': '分',
    '拆分': '拆分', '拆': '拆', '解': '解', '拆解': '拆解',
    '分': '分', '裂': '裂', '分裂': '分裂', '破': '破', '裂': '裂',
    '破裂': '破裂', '断': '斷', '裂': '裂', '断裂': '斷裂',
    '切': '切', '断': '斷', '切断': '切斷', '截': '截', '断': '斷',
    '截断': '截斷', '中': '中', '断': '斷', '中断': '中斷',
    '打': '打', '断': '斷', '打断': '打斷', '阻': '阻', '断': '斷',
    '阻断': '阻斷', '隔': '隔', '断': '斷', '隔断': '隔斷',
    '间': '間', '断': '斷', '间断': '間斷', '连': '連', '续': '續',
    '连续': '連續', '持': '持', '续': '續', '持续': '持續',
    '继': '繼', '续': '續', '继续': '繼續', '延': '延', '续': '續',
    '延续': '延續', '延': '延', '长': '長', '延长': '延長',
    '延': '延', '伸': '伸', '延伸': '延伸', '伸': '伸', '展': '展',
    '伸展': '伸展', '扩': '擴', '展': '展', '扩展': '擴展',
    '拓': '拓', '展': '展', '拓展': '拓展', '展': '展', '开': '開',
    '展开': '展開', '铺': '鋪', '开': '開', '铺开': '鋪開',
    '摊': '攤', '开': '開', '摊开': '攤開', '张': '張', '开': '開',
    '张开': '張開', '撑': '撐', '开': '開', '撑开': '撐開',
    '收': '收', '拢': '攏', '收拢': '收攏', '收': '收', '缩': '縮',
    '收缩': '收縮', '缩': '縮', '小': '小', '缩小': '縮小',
    '缩': '縮', '短': '短', '缩短': '縮短', '压': '壓', '缩': '縮',
    '压缩': '壓縮', '紧': '緊', '缩': '縮', '紧缩': '緊縮',
    '挤': '擠', '压': '壓', '挤压': '擠壓', '挤': '擠', '塞': '塞',
    '挤塞': '擠塞', '拥': '擁', '挤': '擠', '拥挤': '擁擠',
    '拥': '擁', '堵': '堵', '拥堵': '擁堵', '堵': '堵', '塞': '塞',
    '堵塞': '堵塞', '阻': '阻', '塞': '塞', '阻塞': '阻塞',
    '阻': '阻', '挡': '擋', '阻挡': '阻擋', '阻': '阻', '止': '止',
    '阻止': '阻止', '阻': '阻', '碍': '礙', '阻碍': '阻礙',
    '障': '障', '碍': '礙', '障碍': '障礙', '妨': '妨', '碍': '礙',
    '妨碍': '妨礙', '干': '幹', '扰': '擾', '干扰': '幹擾',
    '干': '幹', '涉': '涉', '干涉': '幹涉', '介': '介', '入': '入',
    '介入': '介入', '插': '插', '入': '入', '插入': '插入',
    '切': '切', '入': '入', '切入': '切入', '闯': '闖', '入': '入',
    '闯入': '闖入', '冲': '衝', '入': '入', '冲入': '衝入',
    '进': '進', '入': '入', '进入': '進入', '潜': '潛', '入': '入',
    '潜入': '潛入', '深': '深', '入': '入', '深入': '深入',
    '渗': '滲', '入': '入', '渗入': '滲入', '侵': '侵', '入': '入',
    '侵入': '侵入', '侵': '侵', '犯': '犯', '侵犯': '侵犯',
    '违': '違', '犯': '犯', '违犯': '違犯', '违': '違', '反': '反',
    '违反': '違反', '违': '違', '背': '背', '违背': '違背',
    '违': '違', '章': '章', '违章': '違章', '违': '違', '规': '規',
    '违规': '違規', '违': '違', '法': '法', '违法': '違法',
    '犯': '犯', '法': '法', '犯法': '犯法', '犯': '犯', '罪': '罪',
    '犯罪': '犯罪', '罪': '罪', '行': '行', '罪行': '罪行',
    '错': '錯', '误': '誤', '错误': '錯誤', '失': '失', '误': '誤',
    '失误': '失誤', '过': '過', '失': '失', '过失': '過失',
    '过': '過', '错': '錯', '过错': '過錯', '疏': '疏', '忽': '忽',
    '疏忽': '疏忽', '疏': '疏', '漏': '漏', '疏漏': '疏漏',
    '遗': '遺', '漏': '漏', '遗漏': '遺漏', '遗': '遺', '忘': '忘',
    '遗忘': '遺忘', '忘': '忘', '记': '記', '忘记': '忘記',
    '记': '記', '忆': '憶', '记忆': '記憶', '记': '記', '住': '住',
    '记住': '記住', '记': '記', '录': '錄', '记录': '記錄',
    '记': '記', '载': '載', '记载': '記載', '登': '登', '记': '記',
    '登记': '登記', '注': '注', '册': '冊', '注册': '註冊',
    '注': '注', '明': '明', '注明': '註明', '注': '注', '释': '釋',
    '注释': '註釋', '备': '備', '注': '註', '备注': '備註',
    '标': '標', '注': '註', '标注': '標註', '签': '簽', '名': '名',
    '签名': '簽名', '签': '簽', '字': '字', '签字': '簽字',
    '签': '簽', '署': '署', '签署': '簽署', '签': '簽', '约': '約',
    '签约': '簽約', '签': '簽', '订': '訂', '签订': '簽訂',
    '订': '訂', '立': '立', '订立': '訂立', '制': '制', '订': '訂',
    '制订': '制訂', '拟': '擬', '订': '訂', '拟订': '擬訂',
    '草': '草', '拟': '擬', '草拟': '草擬', '起': '起', '草': '草',
    '起草': '起草', '草': '草', '案': '案', '草案': '草案',
    '方': '方', '案': '案', '方案': '方案', '预': '預', '案': '案',
    '预案': '預案', '备': '備', '案': '案', '备案': '備案',
    '档': '檔', '案': '案', '档案': '檔案', '卷': '卷', '宗': '宗',
    '卷宗': '卷宗', '文': '文', '件': '件', '文件': '文件',
    '证': '證', '件': '件', '证件': '證件', '证': '證', '明': '明',
    '证明': '證明', '证': '證', '书': '書', '证书': '證書',
    '执': '執', '照': '照', '执照': '執照', '许': '許', '可': '可',
    '许可': '許可', '许': '許', '可': '可', '证': '證', '许可证': '許可證',
    '驾': '駕', '照': '照', '驾照': '駕照', '驾': '駕', '驶': '駛',
    '驾驶': '駕駛', '驾': '駕', '驶': '駛', '员': '員', '驾驶员': '駕駛員',
    '司': '司', '机': '機', '司机': '司機', '机': '機', '动': '動',
    '机动': '機動', '电': '電', '动': '動', '电动': '電動',
    '自': '自', '动': '動', '自动': '自動', '手': '手', '动': '動',
    '手动': '手動', '推': '推', '动': '動', '推动': '推動',
    '拉': '拉', '动': '動', '拉动': '拉動', '带': '帶', '动': '動',
    '带动': '帶動', '牵': '牽', '引': '引', '牵引': '牽引',
    '牵': '牽', '动': '動', '牵动': '牽動', '拖': '拖', '动': '動',
    '拖动': '拖動', '拖': '拖', '拉': '拉', '拖拉': '拖拉',
    '拖': '拖', '拽': '拽', '拖拽': '拖拽', '推': '推', '拉': '拉',
    '推拉': '推拉', '推': '推', '挤': '擠', '推挤': '推擠',
    '推': '推', '进': '進', '推进': '推進', '前': '前', '进': '進',
    '前进': '前進', '后': '後', '退': '退', '后退': '後退',
    '倒': '倒', '退': '退', '倒退': '倒退', '倒': '倒', '车': '車',
    '倒车': '倒車', '退': '退', '车': '車', '退车': '退車',
    '停': '停', '车': '車', '停车': '停車', '泊': '泊', '车': '車',
    '泊车': '泊車', '驻': '駐', '车': '車', '驻车': '駐車',
    '靠': '靠', '边': '邊', '靠边': '靠邊', '靠': '靠', '站': '站',
    '靠站': '靠站', '站': '站', '台': '台', '站台': '站台',
    '车': '車', '站': '站', '车站': '車站', '火': '火', '车': '車',
    '火车': '火車', '火': '火', '车': '車', '站': '站', '火车站': '火車站',
    '汽': '汽', '车': '車', '站': '站', '汽车站': '汽車站',
    '地': '地', '铁': '鐵', '地铁': '地鐵', '地': '地', '铁': '鐵',
    '站': '站', '地铁站': '地鐵站', '公': '公', '交': '交',
    '公交': '公交', '公': '公', '交': '交', '站': '站',
    '公交站': '公交站', '巴': '巴', '士': '士', '巴士': '巴士',
    '巴': '巴', '士': '士', '站': '站', '巴士站': '巴士站',
    '出': '出', '租': '租', '出租': '出租', '出': '出', '租': '租',
    '车': '車', '出租车': '出租車', '计': '計', '程': '程',
    '计程': '計程', '计': '計', '程': '程', '车': '車',
    '计程车': '計程車', '的': '的', '士': '士', '的士': '的士',
    '小': '小', '汽': '汽', '小汽': '小汽', '小': '小', '汽': '汽',
    '车': '車', '小汽车': '小汽車', '私': '私', '家': '家',
    '私家': '私家', '私': '私', '家': '家', '车': '車',
    '私家车': '私家車', '家': '家', '用': '用', '家用': '家用',
    '家': '家', '用': '用', '车': '車', '家用车': '家用車',
    '商': '商', '用': '用', '商用': '商用', '商': '商', '用': '用',
    '车': '車', '商用车': '商用車', '工': '工', '程': '程',
    '工程': '工程', '工': '工', '程': '程', '车': '車',
    '工程车': '工程車', '救': '救', '援': '援', '救援': '救援',
    '救': '救', '援': '援', '车': '車', '救援车': '救援車',
    '救': '救', '护': '護', '救护': '救護', '救': '救', '护': '護',
    '车': '車', '救护车': '救護車', '消': '消', '防': '防',
    '消防': '消防', '消': '消', '防': '防', '车': '車',
    '消防车': '消防車', '警': '警', '车': '車', '警车': '警車',
    '巡': '巡', '逻': '邏', '巡逻': '巡邏', '巡': '巡', '逻': '邏',
    '车': '車', '巡逻车': '巡邏車', '特': '特', '种': '種',
    '特种': '特種', '特': '特', '种': '種', '车': '車',
    '特种车': '特種車', '专': '專', '用': '用', '专用': '專用',
    '专': '專', '用': '用', '车': '車', '专用车': '專用車',
    '军': '軍', '用': '用', '军用': '軍用', '军': '軍', '用': '用',
    '车': '車', '军用车': '軍用車', '军': '軍', '车': '車',
    '军车': '軍車', '邮': '郵', '政': '政', '邮政': '郵政',
    '邮': '郵', '政': '政', '车': '車', '邮政车': '郵政車',
    '邮': '郵', '车': '車', '邮车': '郵車', '运': '運', '输': '輸',
    '运输': '運輸', '运': '運', '输': '輸', '车': '車',
    '运输车': '運輸車', '货': '貨', '运': '運', '货运': '貨運',
    '货': '貨', '运': '運', '车': '車', '货运车': '貨運車',
    '货': '貨', '车': '車', '货车': '貨車', '客': '客', '运': '運',
    '客运': '客運', '客': '客', '运': '運', '车': '車',
    '客运车': '客運車', '客': '客', '车': '車', '客车': '客車',
    '旅': '旅', '游': '遊', '旅游': '旅遊', '旅': '旅', '游': '遊',
    '车': '車', '旅游车': '旅遊車', '校': '校', '车': '車',
    '校车': '校車', '班': '班', '车': '車', '班车': '班車',
    '通': '通', '勤': '勤', '通勤': '通勤', '通': '通', '勤': '勤',
    '车': '車', '通勤车': '通勤車',
}

def convert_simplified_to_traditional(text: str) -> str:
    """將簡體中文轉換為繁體中文"""
    if not text:
        return text

    result = text

    # 按照長度排序，先替換較長的詞彙
    sorted_conversions = sorted(SIMPLIFIED_TO_TRADITIONAL.items(), key=lambda x: len(x[0]), reverse=True)

    for simplified, traditional in sorted_conversions:
        if simplified in result:
            result = result.replace(simplified, traditional)

    return result

class ShockwaveAnalysisRequest(BaseModel):
    user_location: Dict[str, float]  # {lat, lng}
    shockwaves: List[Dict[str, Any]]
    user_message: Optional[str] = "請分析當前的交通衝擊波情況並給予建議"
    destination: Optional[Dict[str, float]] = None

class ShockwaveRecommendation(BaseModel):
    type: str  # "alternative_route", "timing_adjustment", "rest_area", "speed_warning", "emergency"
    priority: str  # "urgent", "high", "medium", "low"
    title: str
    description: str
    action_time: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

class ShockwaveAnalysisResponse(BaseModel):
    recommendations: List[ShockwaveRecommendation]
    risk_level: str  # "high", "medium", "low"
    summary: str
    ai_analysis: str

def get_approximate_location(lat: float, lng: float) -> str:
    """根據座標判斷台灣地區位置"""
    regions = [
        # 新北市
        {'name': '新北市淡水區', 'bounds': {'north': 25.22, 'south': 25.15, 'east': 121.47, 'west': 121.41}},
        {'name': '新北市三重區', 'bounds': {'north': 25.08, 'south': 25.04, 'east': 121.50, 'west': 121.47}},
        {'name': '新北市板橋區', 'bounds': {'north': 25.02, 'south': 24.98, 'east': 121.47, 'west': 121.43}},
        {'name': '新北市中和區', 'bounds': {'north': 25.00, 'south': 24.95, 'east': 121.52, 'west': 121.47}},
        {'name': '新北市永和區', 'bounds': {'north': 25.02, 'south': 24.98, 'east': 121.52, 'west': 121.50}},
        {'name': '新北市新店區', 'bounds': {'north': 25.00, 'south': 24.93, 'east': 121.55, 'west': 121.50}},
        {'name': '新北市土城區', 'bounds': {'north': 24.98, 'south': 24.93, 'east': 121.47, 'west': 121.40}},
        {'name': '新北市蘆洲區', 'bounds': {'north': 25.10, 'south': 25.07, 'east': 121.48, 'west': 121.45}},
        {'name': '新北市五股區', 'bounds': {'north': 25.12, 'south': 25.07, 'east': 121.45, 'west': 121.41}},
        {'name': '新北市泰山區', 'bounds': {'north': 25.07, 'south': 25.04, 'east': 121.43, 'west': 121.40}},
        {'name': '新北市林口區', 'bounds': {'north': 25.12, 'south': 25.06, 'east': 121.40, 'west': 121.35}},

        # 台北市
        {'name': '台北市中正區', 'bounds': {'north': 25.05, 'south': 25.03, 'east': 121.53, 'west': 121.51}},
        {'name': '台北市大同區', 'bounds': {'north': 25.07, 'south': 25.04, 'east': 121.52, 'west': 121.50}},
        {'name': '台北市中山區', 'bounds': {'north': 25.08, 'south': 25.05, 'east': 121.55, 'west': 121.52}},
        {'name': '台北市松山區', 'bounds': {'north': 25.07, 'south': 25.04, 'east': 121.58, 'west': 121.55}},
        {'name': '台北市大安區', 'bounds': {'north': 25.04, 'south': 25.01, 'east': 121.56, 'west': 121.53}},
        {'name': '台北市萬華區', 'bounds': {'north': 25.04, 'south': 25.01, 'east': 121.51, 'west': 121.48}},
        {'name': '台北市信義區', 'bounds': {'north': 25.05, 'south': 25.02, 'east': 121.58, 'west': 121.55}},
        {'name': '台北市士林區', 'bounds': {'north': 25.12, 'south': 25.08, 'east': 121.55, 'west': 121.50}},
        {'name': '台北市北投區', 'bounds': {'north': 25.15, 'south': 25.10, 'east': 121.53, 'west': 121.48}},
        {'name': '台北市內湖區', 'bounds': {'north': 25.10, 'south': 25.06, 'east': 121.60, 'west': 121.55}},
        {'name': '台北市南港區', 'bounds': {'north': 25.07, 'south': 25.03, 'east': 121.62, 'west': 121.58}},
        {'name': '台北市文山區', 'bounds': {'north': 25.01, 'south': 24.97, 'east': 121.57, 'west': 121.53}},

        # 桃園市
        {'name': '桃園市桃園區', 'bounds': {'north': 25.00, 'south': 24.95, 'east': 121.32, 'west': 121.28}},
        {'name': '桃園市中壢區', 'bounds': {'north': 24.98, 'south': 24.93, 'east': 121.25, 'west': 121.20}},
        {'name': '桃園市平鎮區', 'bounds': {'north': 24.95, 'south': 24.90, 'east': 121.25, 'west': 121.20}},
        {'name': '桃園市八德區', 'bounds': {'north': 24.97, 'south': 24.92, 'east': 121.30, 'west': 121.25}},

        # 新竹
        {'name': '新竹市東區', 'bounds': {'north': 24.82, 'south': 24.78, 'east': 120.98, 'west': 120.94}},
        {'name': '新竹市北區', 'bounds': {'north': 24.85, 'south': 24.81, 'east': 120.97, 'west': 120.93}},
        {'name': '新竹市香山區', 'bounds': {'north': 24.78, 'south': 24.74, 'east': 120.94, 'west': 120.90}},
    ]

    # 尋找匹配的區域
    for region in regions:
        bounds = region['bounds']
        if (lat >= bounds['south'] and lat <= bounds['north'] and
            lng >= bounds['west'] and lng <= bounds['east']):
            return region['name']

    # 如果沒有精確匹配，提供大致區域
    if 25.15 <= lat <= 25.22 and 121.40 <= lng <= 121.50:
        return '新北市淡水地區'
    elif 25.00 <= lat <= 25.15 and 121.45 <= lng <= 121.65:
        return '台北都會區'
    elif 24.90 <= lat <= 25.00 and 121.15 <= lng <= 121.35:
        return '桃園市'
    elif 24.70 <= lat <= 24.85 and 120.90 <= lng <= 121.00:
        return '新竹地區'

    # 最後備用：顯示座標
    return f'位置 {lat:.4f}, {lng:.4f}'


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩點之間的距離 (Haversine公式)"""
    R = 6371  # 地球半徑 (公里)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2) * math.sin(dLat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dLon/2) * math.sin(dLon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def analyze_shockwave_risk(user_location: Dict[str, float], shockwaves: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析衝擊波風險等級和基本建議"""
    if not shockwaves:
        return {"risk_level": "low", "nearest_shock": None, "recommendations": []}
    
    nearest_shock = None
    min_distance = float('inf')
    max_intensity = 0
    
    for shock in shockwaves:
        distance = calculate_distance(
            user_location['lat'], user_location['lng'],
            shock.get('latitude', 0), shock.get('longitude', 0)
        )
        shock['distance_to_user'] = distance
        
        if distance < min_distance:
            min_distance = distance
            nearest_shock = shock
        
        if shock.get('intensity', 0) > max_intensity:
            max_intensity = shock.get('intensity', 0)
    
    # 風險等級評估
    if min_distance < 5 and max_intensity >= 7:
        risk_level = "high"
    elif min_distance < 10 and max_intensity >= 5:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "risk_level": risk_level,
        "nearest_shock": nearest_shock,
        "min_distance": min_distance,
        "max_intensity": max_intensity
    }

def generate_recommendations(analysis: Dict[str, Any], shockwaves: List[Dict[str, Any]]) -> List[ShockwaveRecommendation]:
    """根據分析結果生成具體建議"""
    recommendations = []
    nearest_shock = analysis['nearest_shock']
    
    if not nearest_shock:
        return recommendations
    
    distance = analysis['min_distance']
    intensity = analysis['max_intensity']
    risk_level = analysis['risk_level']
    
    # 1. 替代路線建議
    if distance < 15 and intensity >= 6:
        recommendations.append(ShockwaveRecommendation(
            type="alternative_route",
            priority="high" if risk_level == "high" else "medium",
            title="建議使用替代路線",
            description=f"前方{distance:.1f}公里處有強度{intensity}/10的交通衝擊波，建議改走省道或其他國道避開壅塞區域",
            location={"lat": nearest_shock.get('latitude'), "lng": nearest_shock.get('longitude')}
        ))
    
    # 2. 時間調整建議
    duration = nearest_shock.get('shock_duration', 30)
    if distance < 20 and intensity >= 5:
        delay_minutes = max(duration + 10, 20)  # 衝擊波持續時間 + 緩衝時間
        recommendations.append(ShockwaveRecommendation(
            type="timing_adjustment",
            priority="medium",
            title="建議延後出發",
            description=f"衝擊波預計持續{duration}分鐘，建議延後{delay_minutes}分鐘出發，讓衝擊波通過後再行駛",
            action_time=(datetime.now() + timedelta(minutes=delay_minutes)).strftime('%H:%M')
        ))
    
    # 3. 休息站建議
    if distance < 10 and intensity >= 6:
        recommendations.append(ShockwaveRecommendation(
            type="rest_area",
            priority="high" if risk_level == "high" else "medium",
            title="建議前往休息站等待",
            description=f"前方{distance:.1f}公里即將遭受衝擊波影響，建議就近尋找休息站或安全區域等待{duration}分鐘",
            action_time=f"等待約{duration}分鐘"
        ))
    
    # 4. 速度警告
    if distance < 25:
        safe_speed = max(50, 80 - intensity * 5)  # 根據強度調整建議速度
        recommendations.append(ShockwaveRecommendation(
            type="speed_warning",
            priority="medium",
            title="前方需要降速",
            description=f"前方{distance:.1f}公里後車流將受衝擊波影響，建議將車速降至{safe_speed}km/h以下，保持安全跟車距離",
            action_time=f"{distance:.1f}公里後"
        ))
    
    # 5. 緊急措施
    if distance < 3 and intensity >= 8:
        recommendations.append(ShockwaveRecommendation(
            type="emergency",
            priority="urgent",
            title="⚠️ 緊急注意",
            description="您即將進入高強度衝擊波影響區域，請立即減速並尋找安全地點停車，避免追撞風險",
            action_time="立即"
        ))
    
    return recommendations

class SingleShockwaveAnalysisRequest(BaseModel):
    user_location: Dict[str, float]  # {lat, lng}
    shockwave: Dict[str, Any]  # 單個衝擊波資訊
    
@router.post("/shockwave-analysis", response_model=ShockwaveAnalysisResponse)
async def analyze_shockwave_impact(request: ShockwaveAnalysisRequest):
    """分析交通衝擊波對駕駛者的影響並提供具體建議"""
    try:
        # 1. 基本風險分析
        analysis = analyze_shockwave_risk(request.user_location, request.shockwaves)
        
        # 2. 生成具體建議
        recommendations = generate_recommendations(analysis, request.shockwaves)
        
        # 3. 構建簡化的AI分析提示
        nearest_shock = analysis['nearest_shock']
        distance = analysis['min_distance']
        intensity = analysis['max_intensity']

        # 獲取用戶準確位置
        user_location_name = get_approximate_location(request.user_location['lat'], request.user_location['lng'])
        shock_location_name = get_approximate_location(nearest_shock['latitude'], nearest_shock['longitude']) if nearest_shock else '未知位置'

        # 根據衝擊波位置獲取精確的地理資訊
        shock_lat = nearest_shock.get('latitude', 0)
        shock_lng = nearest_shock.get('longitude', 0)
        shock_station_id = nearest_shock.get('station_id', '未知測站')
        shock_station_name = nearest_shock.get('station_name', '未知路段')

        detailed_prompt = f"""你是台灣的專業交通專家，請務必使用繁體中文（Traditional Chinese）進行分析，嚴禁使用簡體字：

【台灣交通衝擊波分析】
用戶位置：{user_location_name}
衝擊波發生位置：{shock_location_name}
衝擊波精確座標：緯度{shock_lat:.6f}, 經度{shock_lng:.6f}
測站編號：{shock_station_id}
路段名稱：{shock_station_name}
距離用戶：{distance:.1f}公里處有強度{intensity}/10的衝擊波
風險等級：{analysis['risk_level']}

【重要】請基於衝擊波實際發生位置（{shock_location_name}）提供建議，不要提及與衝擊波位置無關的其他地區路線。

請針對此衝擊波位置用繁體中文提供：
1. 🛣️ 針對{shock_location_name}衝擊波的具體替代路線（國道/省道）
2. ⏰ 時間調整建議（延後多久出發）
3. 🅿️ {shock_location_name}附近的休息站或安全停靠點
4. 🚗 行車速度和安全距離建議
5. 📱 其他針對性注意事項

重要：請務必使用繁體中文回答，嚴禁使用簡體字，建議必須針對衝擊波實際位置，簡潔回答，200字內："""

        # 4. 使用真實Ollama AI進行分析
        try:
            ollama_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "qwen2.5:14b",
                    "prompt": detailed_prompt,
                    "stream": False
                },
                timeout=30  # 30秒超時
            )
            
            if ollama_response.ok:
                ai_data = ollama_response.json()
                raw_ai_response = ai_data.get('response', '分析中...')
                # 將AI回覆轉換為繁體中文
                converted_ai_response = convert_simplified_to_traditional(raw_ai_response)
                ai_analysis = f"""🤖 AI智能分析報告

📍 衝擊波位置：{nearest_shock.get('location_name', '未知位置')}
📏 距離您的位置：{distance:.1f}公里
📊 衝擊波強度：{intensity}/10
⏱️ 預估持續時間：{nearest_shock.get('shock_duration', '未知')}分鐘
🌊 影響範圍：{nearest_shock.get('affected_area', '未知')}公里

🧠 AI專家建議：
{converted_ai_response}

⚠️ 此分析基於即時AI運算，請結合實際路況謹慎駕駛！"""
            else:
                ai_analysis = f"""⚠️ AI服務暫時不可用

📍 基礎分析報告：
• 衝擊波位置：{nearest_shock.get('location_name', '未知位置')}
• 距離：{distance:.1f}公里
• 強度：{intensity}/10
• 風險等級：{analysis['risk_level'].upper()}

請根據基礎分析謹慎駕駛，安全第一！"""
                
        except Exception as e:
            print(f"Ollama AI 調用失敗: {str(e)}")
            ai_analysis = f"""⚠️ AI分析服務連線異常

📍 緊急基礎分析：
• 檢測到衝擊波距離您{distance:.1f}公里
• 強度等級：{intensity}/10 
• 風險評估：{analysis['risk_level'].upper()}

建議立即關注路況，必要時尋找替代路線！"""
        
        # 5. 生成摘要
        risk_level = analysis['risk_level']
        shock_count = len(request.shockwaves)
        min_distance = analysis['min_distance']
        
        if risk_level == "high":
            summary = f"⚠️ 高風險：檢測到{shock_count}個衝擊波，最近距離{min_distance:.1f}公里，建議立即採取避險措施"
        elif risk_level == "medium":
            summary = f"⚡ 中等風險：檢測到{shock_count}個衝擊波，最近距離{min_distance:.1f}公里，建議調整行駛計畫"
        else:
            summary = f"ℹ️ 低風險：檢測到{shock_count}個衝擊波，距離較遠，請持續關注路況變化"
        
        return ShockwaveAnalysisResponse(
            recommendations=recommendations,
            risk_level=risk_level,
            summary=summary,
            ai_analysis=ai_analysis
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"衝擊波分析失敗: {str(e)}")

@router.get("/shockwave-status")
async def get_shockwave_status():
    """獲取衝擊波分析系統狀態"""
    try:
        # 檢查Ollama服務
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if response.ok else "unavailable"
        
        return {
            "status": "operational",
            "ollama_status": ollama_status,
            "features": {
                "distance_calculation": True,
                "risk_assessment": True,
                "recommendation_engine": True,
                "ai_analysis": ollama_status == "healthy"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/single-shockwave-analysis")
async def analyze_single_shockwave(request: SingleShockwaveAnalysisRequest):
    """針對特定衝擊波進行詳細AI分析"""
    try:
        # 計算距離
        user_lat = request.user_location['lat']
        user_lng = request.user_location['lng']
        shock_lat = request.shockwave['latitude']
        shock_lng = request.shockwave['longitude']

        distance = calculate_distance(user_lat, user_lng, shock_lat, shock_lng)
        intensity = request.shockwave.get('intensity', 0)

        # 獲取準確的地理位置
        user_location_name = get_approximate_location(user_lat, user_lng)
        shock_location_name = get_approximate_location(shock_lat, shock_lng)

        # 風險評估
        if distance < 5 and intensity > 8:
            risk_level = "high"
        elif distance < 15 and intensity > 6:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 構建詳細的AI分析提示
        shock_info = request.shockwave
        shock_station_id = shock_info.get('station_id', '未知測站')
        shock_station_name = shock_info.get('station_name', '未知路段')

        ai_prompt = f"""你是台灣的專業交通專家，請務必使用繁體中文（Traditional Chinese）分析以下衝擊波情況並提供專業建議，嚴禁使用簡體字：

【衝擊波詳細資訊】
• 發生位置：{shock_location_name}
• 測站編號：{shock_station_id}
• 路段名稱：{shock_station_name}
• 精確座標：緯度{shock_lat:.6f}，經度{shock_lng:.6f}
• 距離用戶：{distance:.1f}公里
• 強度等級：{intensity}/10
• 持續時間：{shock_info.get('shock_duration', '未知')}分鐘
• 影響範圍：{shock_info.get('affected_area', '未知')}公里
• 傳播速度：{shock_info.get('propagation_speed', '未知')}km/h
• 預估降速：{shock_info.get('speed_drop', '未知')}%

【使用者位置】
位置：{user_location_name}
精確座標：緯度{user_lat:.6f}，經度{user_lng:.6f}

【重要】請基於衝擊波實際發生位置（{shock_location_name}）提供建議，不要提及與衝擊波位置無關的其他地區路線。

請針對{shock_location_name}衝擊波用繁體中文提供：
1. 🛣️ 針對{shock_location_name}的具體替代路線建議（國道/省道）
2. ⏰ 精確的時間調整建議（何時出發最佳）
3. 🅿️ {shock_location_name}附近休息站或安全停靠點
4. 🚗 行車速度和安全距離建議
5. 📱 其他針對性注意事項

重要：請務必使用繁體中文回答，嚴禁使用任何簡體字，建議必須針對衝擊波實際位置，以專業、簡潔的方式回答，控制在200字內："""

        # 調用真實AI分析
        try:
            ollama_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "qwen2.5:14b",
                    "prompt": ai_prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if ollama_response.ok:
                ai_data = ollama_response.json()
                raw_analysis = ai_data.get('response', '分析中...')
                # 將AI回覆轉換為繁體中文
                ai_analysis = convert_simplified_to_traditional(raw_analysis)
            else:
                raise Exception("Ollama API 請求失敗")
                
        except Exception as e:
            print(f"AI分析失敗: {str(e)}")
            ai_analysis = f"""⚠️ AI服務暫時無法使用，提供基礎分析：

基於衝擊波資料分析：
• 距離{distance:.1f}公里的{shock_info.get('location_name', '衝擊波區域')}
• 強度{intensity}/10，風險等級：{risk_level.upper()}
• 建議採取相應的預防措施

請根據實際路況謹慎駕駛！"""

        # 生成針對性建議
        recommendations = []
        if distance < 15 and intensity >= 6:
            recommendations.append({
                "type": "alternative_route",
                "priority": "high" if risk_level == "high" else "medium",
                "title": "替代路線建議",
                "description": f"前方{distance:.1f}公里處的{shock_info.get('location_name', '衝擊波區域')}強度達{intensity}/10，建議改走替代路線"
            })
        
        if distance < 20:
            delay_time = shock_info.get('shock_duration', 30) + 15
            recommendations.append({
                "type": "timing_adjustment", 
                "priority": "medium",
                "title": "出行時間調整",
                "description": f"建議延後{delay_time}分鐘出發，避開衝擊波高峰期"
            })
        
        return {
            "shockwave_info": shock_info,
            "distance": round(distance, 1),
            "risk_level": risk_level,
            "ai_analysis": ai_analysis,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"單衝擊波分析失敗: {str(e)}")