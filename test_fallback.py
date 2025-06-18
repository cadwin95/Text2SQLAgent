#!/usr/bin/env python3
"""
Fallback 시스템 테스트 스크립트
=============================
KOSIS Fallback 시스템의 기능을 테스트합니다.
"""

import json
from kosis_fallback import analyze_data_question

def test_fallback_system():
    """Fallback 시스템 테스트"""
    print("🔄 KOSIS Fallback 시스템 테스트")
    print("=" * 50)
    
    # 테스트 질문들
    test_questions = [
        "한국의 인구 통계를 보여주세요",
        "GDP 성장률을 분석해주세요",
        "물가지수 추이를 알려주세요",
        "고용률 통계를 조회해주세요",
        "지역별 경제지표를 비교해주세요",
        "최근 5년간 인구 변화를 분석해주세요"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}️⃣ 질문: {question}")
        print("-" * 40)
        
        try:
            # Fallback 데이터 조회
            result = analyze_data_question(question)
            
            # 결과 출력
            print(f"📊 응답 타입: {result.get('response_type', 'unknown')}")
            print(f"🔍 감지된 키워드: {', '.join(result.get('detected_keywords', []))}")
            
            # 데이터 확인
            if 'data' in result:
                data = result['data']
                if isinstance(data, list) and len(data) > 0:
                    print(f"📈 데이터 개수: {len(data)}개")
                    print(f"📋 첫 번째 항목: {json.dumps(data[0], ensure_ascii=False, indent=2)}")
                else:
                    print(f"📋 데이터: {data}")
            
            # 분석 정보 확인
            if 'analysis' in result:
                analysis = result['analysis']
                print(f"📊 분석:")
                for key, value in analysis.items():
                    print(f"   - {key}: {value}")
            
            # 추천 사항 확인
            if 'recommendations' in result:
                recommendations = result['recommendations']
                print(f"💡 추천사항: {len(recommendations)}개")
                for rec in recommendations:
                    print(f"   - {rec}")
            
            print("✅ 성공")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print(f"\n🎉 Fallback 시스템 테스트 완료!")

def test_specific_categories():
    """특정 카테고리별 테스트"""
    print("\n📂 카테고리별 상세 테스트")
    print("=" * 50)
    
    categories = {
        "인구": "2023년 한국 인구는 얼마인가요?",
        "경제": "한국의 GDP는 어떻게 변화했나요?",
        "물가": "최근 물가지수 상승률을 알려주세요",
        "고용": "청년 실업률 통계를 보여주세요",
        "지역": "서울과 부산의 인구를 비교해주세요"
    }
    
    for category, question in categories.items():
        print(f"\n🏷️ {category} 카테고리 테스트")
        print(f"❓ 질문: {question}")
        
        try:
            result = analyze_data_question(question)
            
            # 카테고리 매칭 확인
            response_type = result.get('response_type', '')
            if category.lower() in response_type.lower():
                print(f"✅ 카테고리 매칭 성공: {response_type}")
            else:
                print(f"⚠️ 카테고리 매칭 주의: 예상={category}, 실제={response_type}")
            
            # 데이터 품질 확인
            if 'data' in result and result['data']:
                print(f"📊 데이터 품질: 양호 ({len(result['data'])}개 항목)")
            else:
                print("📊 데이터 품질: 부족")
                
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_fallback_system()
    test_specific_categories() 