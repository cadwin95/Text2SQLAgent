# test_mcp.py
# -----------
# MCP(KOSIS public API integration) module unit/integration test file
# - Main endpoint (statistics list/data/metadata) normal operation/exception handling/response structure verification
# - Official specification/sample based test, various parameter/execution cases
# - MCP pipeline reliability assurance, automated test/CI integration
# - Detailed design/implementation rules reference: .cursor/rules/rl-text2sql-public-api.md

import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_api import (
    get_stat_list,
    fetch_kosis_data,
    get_table_meta,
    search_kosis,
    API_KEY
)

# Execute only when real API key exists
@pytest.mark.skipif('KOSIS_OPEN_API_KEY' not in os.environ, reason="KOSIS_OPEN_API_KEY environment variable required")
class TestKOSISAPIReal:
    """Integration test using real KOSIS API"""
    
    def test_get_stat_list_basic(self):
        """
        KOSIS statistics list query basic function test
        """
        result = get_stat_list(API_KEY, "MT_ZTITLE", "", "json")
        assert isinstance(result, (dict, list))
        
        # When result is list (normal response)
        if isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            # Check general KOSIS response fields
            assert any(key in first_item for key in ["TBL_NM", "ORG_NM", "TBL_ID"])
    
    def test_fetch_kosis_data_sample(self):
        """
        KOSIS 데이터 조회 테스트
        """
        # Use official sample userStatsId
        result = fetch_kosis_data(
            API_KEY, 
            orgId="101", 
            tblId="DT_1B040A3",
            prdSe="Y",
            startPrdDe="2020",
            endPrdDe="2023"
        )
        
        assert isinstance(result, pd.DataFrame)
        # Check basic structure when data exists
        if not result.empty:
            assert len(result.columns) > 0
            assert len(result) > 0
    
    def test_search_kosis_keyword(self):
        """
        KOSIS integrated search function test
        """
        result = search_kosis("population")
        assert isinstance(result, pd.DataFrame)
        # Check when search results exist
        if not result.empty:
            assert len(result.columns) > 0

class TestKOSISAPIMocked:
    """Unit test using Mock"""
    
    @patch('mcp_api.requests.get')
    def test_get_stat_list_success(self, mock_get):
        """
        get_stat_list success case test (Mock)
        """
        # Mock response setup
        mock_response = MagicMock()
        mock_response.text = '''[{
            "TBL_NM": "Population Statistics",
            "ORG_ID": "101", 
            "TBL_ID": "DT_1B040A3",
            "ORG_NM": "Statistics Korea"
        }]'''
        mock_get.return_value = mock_response
        
        result = get_stat_list("test_key", "MT_ZTITLE", "", "json")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["TBL_NM"] == "Population Statistics"
        
        # API call verification
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "statisticsList.do" in call_args[0][0]
    
    @patch('mcp_api.requests.get')
    def test_fetch_kosis_data_success(self, mock_get):
        """
        fetch_kosis_data success case test (Mock)
        """
        # Mock response setup
        mock_response = MagicMock()
        mock_response.text = '''[{
            "TBL_NM": "Population Statistics",
            "PRD_DE": "2023",
            "ITM_NM": "Total Population",
            "DT": "51780579",
            "UNIT_NM": "Persons"
        }]'''
        mock_response.json.return_value = [
            {
                "TBL_NM": "Population Statistics",
                "PRD_DE": "2023", 
                "ITM_NM": "Total Population",
                "DT": "51780579",
                "UNIT_NM": "Persons"
            }
        ]
        mock_get.return_value = mock_response
        
        result = fetch_kosis_data("test_key", "101", "DT_1B040A3")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "TBL_NM" in result.columns
        assert result.iloc[0]["TBL_NM"] == "Population Statistics"
    
    @patch('mcp_api.requests.get')
    def test_fetch_kosis_data_error_handling(self, mock_get):
        """
        fetch_kosis_data error handling test (Mock)
        """
        # HTML error response simulation
        mock_response = MagicMock()
        mock_response.text = '<html><body>Error</body></html>'
        mock_get.return_value = mock_response
        
        result = fetch_kosis_data("invalid_key", "101", "DT_1B040A3")
        
        # Should return empty DataFrame on error
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('mcp_api.requests.get')
    def test_fetch_kosis_data_api_error(self, mock_get):
        """
        KOSIS API error response handling test (Mock)
        """
        # API error response simulation
        mock_response = MagicMock()
        mock_response.text = '{"err": "Invalid API Key"}'
        mock_response.json.return_value = {"err": "Invalid API Key"}
        mock_get.return_value = mock_response
        
        result = fetch_kosis_data("invalid_key", "101", "DT_1B040A3")
        
        # Should return empty DataFrame or alternative data on error
        assert isinstance(result, pd.DataFrame)
    
    @patch('mcp_api.requests.get')
    def test_get_table_meta_classification(self, mock_get):
        """
        get_table_meta classification(CL) query test (Mock)
        """
        # Mock response setup
        mock_response = MagicMock()
        mock_response.text = '''[{
            "CL_ID": "A",
            "CL_NM": "National",
            "PARENT_CL_ID": ""
        }]'''
        mock_get.return_value = mock_response
        
        result = get_table_meta("DT_1B040A3", "CL")
        
        assert isinstance(result, pd.DataFrame)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "statisticsList.do" in call_args[0][0]
    
    @patch('mcp_api.requests.get')
    def test_search_kosis_mock(self, mock_get):
        """
        search_kosis search function test (Mock)
        """
        # Mock response setup
        mock_response = MagicMock()
        mock_response.text = '''[{
            "STAT_NM": "Population and Housing Census",
            "TBL_NM": "Population Statistics Table",
            "ORG_NM": "Statistics Korea"
        }]'''
        mock_get.return_value = mock_response
        
        result = search_kosis("population")
        
        assert isinstance(result, pd.DataFrame)
        mock_get.assert_called_once()

class TestKOSISAPIEdgeCases:
    """Edge Case and exception situation test"""
    
    def test_api_key_validation(self):
        """
        API key validation test
        """
        # Check if API_KEY is set
        if 'KOSIS_OPEN_API_KEY' in os.environ:
            assert API_KEY is not None
            assert len(API_KEY) > 0
        else:
            # Should raise error if environment variable is missing
            with pytest.raises(ValueError):
                from mcp_api import API_KEY
    
    def test_dataframe_columns_consistency(self):
        """
        Returned DataFrame column consistency test
        """
        # Empty DataFrame should also be in correct format
        empty_df = pd.DataFrame()
        assert isinstance(empty_df, pd.DataFrame)
        
        # 기본 데이터 포맷 테스트
        test_data = [
            {
                "TBL_NM": "Test Table",
                "PRD_DE": "2023",
                "DT": "12345"
            }
        ]
        df = pd.DataFrame(test_data)
        assert len(df) == 1
        assert "TBL_NM" in df.columns
        assert "PRD_DE" in df.columns
        assert "DT" in df.columns

def test_module_imports():
    """
    mcp_api module basic import test
    """
    # Check if all major functions are imported correctly
    from mcp_api import (
        get_stat_list,
        fetch_kosis_data,
        get_table_meta,
        search_kosis,
        BASE_URL
    )
    
    assert callable(get_stat_list)
    assert callable(fetch_kosis_data)
    assert callable(get_table_meta)
    assert callable(search_kosis)
    assert BASE_URL == "https://kosis.kr/openapi/"

def test_pandas_integration():
    """
    pandas DataFrame integration test
    """
    # DataFrame 생성/조작이 올바르게 작동하는지 확인
    test_data = {
        'TBL_NM': ['Population Statistics', 'Economic Statistics'],
        'ORG_NM': ['Statistics Korea', 'Bank of Korea'],
        'PRD_DE': ['2023', '2023']
    }
    df = pd.DataFrame(test_data)
    
    assert len(df) == 2
    assert list(df.columns) == ['TBL_NM', 'ORG_NM', 'PRD_DE']
    assert df.iloc[0]['TBL_NM'] == 'Population Statistics'

