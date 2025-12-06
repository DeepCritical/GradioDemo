import unittest
import os
import sys
from pydantic import ValidationError

# Add the src directory to the path so we can import the new schemas module
# Note: This is necessary because src/core is a new folder structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the newly created Pydantic models
# These schemas are foundational for the 'pure Pydantic implementation' for multi-agent systems
from src.core.schemas import (
    ResearchGoal,
    ToolUsage,
    AnalysisStep,
    FinancialAnalysisResult,
    MCPToolDefinition
)

class TestAgentDataSchemas(unittest.TestCase):
    """
    Tests the integrity of the core Pydantic data models used for agent communication
    and output validation, ensuring data reliability for enterprise use.
    """

    def test_research_goal_successful_validation(self):
        """Should validate a ResearchGoal with all fields provided."""
        goal_data = {
            "query": "Analyze Qwen's market position for the next quarter.",
            "investment_target": "Qwen-LLM",
            "time_horizon": "Q3 2025",
            "required_format": "Detailed Analysis"
        }
        try:
            ResearchGoal(**goal_data)
        except ValidationError as e:
            self.fail(f"ResearchGoal validation failed unexpectedly: {e}")

    def test_research_goal_missing_required_field(self):
        """Should fail validation if the 'query' field is missing."""
        invalid_data = {
            "investment_target": "Alibaba stock",
            "time_horizon": "6 months"
        }
        with self.assertRaises(ValidationError) as cm:
            ResearchGoal(**invalid_data)

        # Check that the error pertains to the missing 'query' field
        self.assertIn('query', str(cm.exception))

    def test_tool_usage_successful_validation(self):
        """Should validate a ToolUsage instance."""
        tool_data = {
            "tool_name": "AkshareDataGetter",
            "arguments": {"stock_code": "600000.SH", "period": "weekly"},
            "result_summary": "Retrieved 52 weeks of trading data."
        }
        try:
            ToolUsage(**tool_data)
        except ValidationError as e:
            self.fail(f"ToolUsage validation failed unexpectedly: {e}")

    def test_analysis_step_with_nested_tool_usage(self):
        """Should validate an AnalysisStep that includes ToolUsage records."""
        tool_data = ToolUsage(
            tool_name="BaostockAPI",
            arguments={"query": "financial reports"},
            result_summary="Acquired 2024 earnings report."
        ).model_dump() # Use model_dump() for Pydantic V2

        step_data = {
            "agent_id": "DataGatherer-A",
            "action": "Acquiring Q4 2024 reports.",
            "tools_used": [tool_data],
            "reasoning": "Need current financials for valuation model."
        }

        try:
            AnalysisStep(**step_data)
        except ValidationError as e:
            self.fail(f"AnalysisStep validation failed unexpectedly: {e}")

    def test_financial_analysis_result_successful_validation(self):
        """Should validate the final report structure, including float confidence score."""
        valid_result = {
            "summary": "Qwen LLM market share is growing rapidly in Asia.",
            "key_recommendation": "Strong Buy signal.",
            "analysis_steps": [], # Optional list, can be empty
            "data_sources": ["ModelScope.cn", "Official Press Release"],
            "confidence_score": 0.85
        }
        try:
            result = FinancialAnalysisResult(**valid_result)
            self.assertIsInstance(result.confidence_score, float)
        except ValidationError as e:
            self.fail(f"FinancialAnalysisResult validation failed unexpectedly: {e}")

    def test_financial_analysis_result_invalid_confidence_score_type(self):
        """
        Should fail if confidence_score is not a valid number (e.g., a string).
        (Updated assertion for Pydantic V2 error message)
        """
        invalid_result = {
            "summary": "Test",
            "key_recommendation": "Hold",
            "analysis_steps": [],
            "data_sources": [],
            "confidence_score": "high" # Should be float
        }
        with self.assertRaises(ValidationError) as cm:
            FinancialAnalysisResult(**invalid_result)
        # V2 error message often contains 'unable to parse string as a number'
        self.assertIn('unable to parse string as a number', str(cm.exception))

    def test_mcp_tool_definition_successful_validation(self):
        """Should validate the MCP definition, especially the HttpUrl field."""
        # The application exposes an MCP server endpoint
        mcp_data = {
            "name": "TheDeterminatorsSearch",
            "description": "Performs deep financial research.",
            "endpoint_url": "http://localhost:7860/gradio_api/mcp/"
        }
        try:
            MCPToolDefinition(**mcp_data)
        except ValidationError as e:
            self.fail(f"MCPToolDefinition validation failed unexpectedly: {e}")

    def test_mcp_tool_definition_invalid_url(self):
        """Should fail if the endpoint_url is not a valid URL format."""
        invalid_mcp_data = {
            "name": "InvalidTool",
            "description": "Test",
            "endpoint_url": "not a url"
        }
        with self.assertRaises(ValidationError) as cm:
            MCPToolDefinition(**invalid_mcp_data)

        # Pydantic V2 URL validation error
        self.assertIn('url_parsing', str(cm.exception))

if __name__ == '__main__':
    unittest.main()

