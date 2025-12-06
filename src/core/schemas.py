from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl

# --- Core Data Models for the Financial Research Agent System ---
# This module implements the "pure Pydantic implementation for multi-agent systems"
# required to standardize data flow and enhance commercial reliability.

class ResearchGoal(BaseModel):
    """
    Defines the structured input request received from the Gradio UI or the MCP client.
    This serves as the initial contract for the entire agent workflow.
    """
    query: str = Field(..., description="The high-level financial research question or task.")
    investment_target: Optional[str] = Field(None, description="Specific company, sector, or asset under investigation.")
    time_horizon: str = Field("Next 12 months", description="The required time frame for the analysis (e.g., '6 months', 'long-term').")
    required_format: str = Field("Comprehensive Report", description="The desired output format (e.g., 'Summary', 'Detailed Analysis', 'Presentation Slides').")

class ToolUsage(BaseModel):
    """
    Details of a specific tool utilized during a research step (e.g., using a data acquisition tool like Akshare or Baostock, which were relevant in the ModelScope context).
    """
    tool_name: str = Field(..., description="The name of the external tool or function used.")
    arguments: Dict[str, Any] = Field(..., description="The arguments passed to the tool.")
    result_summary: str = Field(..., description="A summary of the information retrieved or action taken by the tool.")

class AnalysisStep(BaseModel):
    """
    Represents an intermediate step in the multi-agent research process (the iterative search-and-judge loops).
    """
    agent_id: str = Field(..., description="Identifier of the agent responsible for this step.")
    action: str = Field(..., description="Description of the agent's action (e.g., 'Searching market data', 'Synthesizing conflicting reports').")
    tools_used: List[ToolUsage] = Field(default_factory=list, description="List of specific tool calls made during this step.")
    reasoning: str = Field(..., description="The rationale for the agent's action.")

class FinancialAnalysisResult(BaseModel):
    """
    Defines the final, structured output (the monetizable product) delivered by the agent system.
    This structure ensures the output is professional and dependable for enterprise users.
    """
    summary: str = Field(..., description="A concise executive summary of the findings.")
    key_recommendation: str = Field(..., description="The primary investment or business recommendation based on the research.")
    analysis_steps: List[AnalysisStep] = Field(default_factory=list, description="A verifiable trace of all steps taken by the agents.")
    data_sources: List[str] = Field(default_factory=list, description="List of reliable sources used, including links or references.")
    confidence_score: float = Field(..., description="A quantitative score (0.0 to 1.0) reflecting the system's confidence in the recommendation.")

class MCPToolDefinition(BaseModel):
    """
    Schema for defining a tool that is exposed via the Model Context Protocol (MCP) server endpoint.
    This facilitates integration with external clients like Claude Desktop.
    """
    name: str = Field(..., description="The name of the tool exposed via MCP.")
    description: str = Field(..., description="A brief description of what the tool does.")
    endpoint_url: HttpUrl = Field(..., description="The API endpoint URL for the tool.")
