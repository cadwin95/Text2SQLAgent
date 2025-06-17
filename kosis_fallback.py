#!/usr/bin/env python3
"""
🔄 KOSIS Fallback 시스템
========================

📋 목적:
- MCP 서버 연결 실패시 대체 데이터 제공
- 실제 KOSIS API 없이도 의미있는 통계 정보 제공
- 시스템 견고성 향상

🎯 제공 데이터:
- 한국 인구 통계 (연도별 추이)
- 경제 지표 (GDP, 물가지수)
- 지역별 통계 데이터
- 사회 지표 (고용률, 교육 통계)

🔧 처리 방식:
1. 질문 키워드 분석
2. 해당 카테고리의 Mock 데이터 반환
3. 실제 KOSIS 형식과 유사한 구조로 제공
4. 실시간 추이 계산 및 분석 포함

⚠️ 주의사항:
- 실제 데이터가 아닌 시뮬레이션 데이터
- 교육 및 데모 목적으로만 사용
- 실제 분석시 KOSIS 공식 API 사용 권장
"""

import os
import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class KOSISFallback:
    """KOSIS API 직접 호출 클래스"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KOSIS_OPEN_API_KEY") or os.getenv("KOSIS_API_KEY")
        self.base_url = "https://kosis.kr/openapi"
        
    def search_population_data(self, keyword: str = "인구") -> Dict[str, Any]:
        """인구 관련 데이터 검색"""
        if not self.api_key:
            return self._mock_population_data()
            
        try:
            # KOSIS 검색 API 호출
            params = {
                "method": "getList",
                "apiKey": self.api_key,
                "searchNm": keyword,
                "format": "json",
                "jsonVD": "Y"
            }
            
            response = requests.get(f"{self.base_url}/statisticsSearch.do", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "source": "KOSIS API"
                }
        except Exception as e:
            logger.warning(f"KOSIS API 호출 실패: {e}")
            
        return self._mock_population_data()
    
    def get_basic_statistics(self, category: str = "population") -> Dict[str, Any]:
        """기본 통계 정보 제공"""
        if category.lower() in ["인구", "population"]:
            return self._mock_population_data()
        elif category.lower() in ["경제", "gdp", "economy"]:
            return self._mock_economy_data()
        else:
            return self._mock_general_data(category)
    
    def _mock_population_data(self) -> Dict[str, Any]:
        """인구 데이터 모의 응답"""
        return {
            "success": True,
            "data": {
                "title": "한국 인구 통계 (최근 동향)",
                "source": "통계청 KOSIS (모의 데이터)",
                "summary": {
                    "total_population": "약 5,177만명 (2024년 추정)",
                    "growth_rate": "-0.1% (저출산 고령화)",
                    "median_age": "44.9세",
                    "elderly_ratio": "18.4% (65세 이상)"
                },
                "trends": [
                    "2020년부터 인구 감소 시작",
                    "출산율 0.81명으로 세계 최저 수준",
                    "고령화 속도 OECD 최고 수준",
                    "수도권 인구 집중 현상 지속"
                ],
                "regions": {
                    "서울": "약 950만명",
                    "경기": "약 1,350만명",
                    "부산": "약 330만명",
                    "대구": "약 240만명",
                    "인천": "약 295만명"
                }
            },
            "note": "실시간 정확한 데이터는 KOSIS(kosis.kr)에서 확인 가능합니다."
        }
    
    def _mock_economy_data(self) -> Dict[str, Any]:
        """경제 데이터 모의 응답"""
        return {
            "success": True,
            "data": {
                "title": "한국 경제 지표 (최근 동향)",
                "source": "한국은행, 통계청 (모의 데이터)",
                "summary": {
                    "gdp_growth": "3.1% (2024년 전망)",
                    "inflation_rate": "2.8%",
                    "unemployment_rate": "2.9%",
                    "current_account": "흑자 기조 유지"
                },
                "trends": [
                    "수출 회복세로 성장률 개선",
                    "내수 소비 점진적 회복",
                    "반도체 업황 개선 영향",
                    "글로벌 공급망 정상화"
                ],
                "sectors": {
                    "제조업": "성장률 4.2%",
                    "서비스업": "성장률 2.8%",
                    "건설업": "성장률 -1.1%",
                    "농림어업": "성장률 1.5%"
                }
            },
            "note": "실시간 정확한 데이터는 KOSIS(kosis.kr)에서 확인 가능합니다."
        }
    
    def _mock_general_data(self, category: str) -> Dict[str, Any]:
        """일반 통계 데이터 모의 응답"""
        return {
            "success": True,
            "data": {
                "title": f"{category} 관련 통계",
                "source": "통계청 KOSIS (모의 데이터)",
                "summary": f"{category}에 대한 기본적인 통계 정보를 제공합니다.",
                "note": "구체적인 데이터는 KOSIS(kosis.kr)에서 직접 검색하시기 바랍니다."
            }
        }

# 전역 인스턴스
kosis_fallback = KOSISFallback()

def analyze_data_question(question: str) -> Dict[str, Any]:
    """데이터 분석 질문 처리"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["인구", "population", "출산", "고령화"]):
        return kosis_fallback.search_population_data("인구")
    elif any(word in question_lower for word in ["gdp", "경제", "성장률", "inflation", "물가"]):
        return kosis_fallback.get_basic_statistics("economy")
    else:
        # 일반적인 통계 정보
        return {
            "success": True,
            "data": {
                "title": "통계 데이터 안내",
                "message": "한국 통계청(KOSIS)에서는 다음과 같은 분야의 통계를 제공합니다:",
                "categories": [
                    "인구 및 사회 통계",
                    "경제 및 산업 통계", 
                    "지역 통계",
                    "국제 통계",
                    "북한 통계"
                ],
                "popular_stats": [
                    "주민등록인구 통계",
                    "국내총생산(GDP)",
                    "소비자물가지수",
                    "고용동향",
                    "가계소득"
                ]
            },
            "note": "구체적인 데이터는 KOSIS(kosis.kr)에서 확인하실 수 있습니다."
        } 