# Report Writing Agents Analysis

## Summary

This document identifies all agents and methods in the repository that generate reports or write to files.

## Key Finding

**All report-writing agents return strings (markdown) - NONE write directly to files.**

The agents generate report content but do not save it to disk. File writing would need to be added as a separate step.

---

## Report Writing Agents

### 1. WriterAgent
**File**: `src/agents/writer.py`

**Method**: `async def write_report(query, findings, output_length, output_instructions) -> str`

**Returns**: Markdown formatted report string

**Purpose**: Generates final reports from research findings with numbered citations

**File Writing**: ❌ **NO** - Returns string only

**Key Features**:
- Validates inputs
- Truncates very long findings (max 50,000 chars)
- Retry logic (3 retries)
- Returns markdown with numbered citations

---

### 2. LongWriterAgent
**File**: `src/agents/long_writer.py`

**Methods**:
- `async def write_next_section(original_query, report_draft, next_section_title, next_section_draft) -> LongWriterOutput`
- `async def write_report(original_query, report_title, report_draft) -> str`

**Returns**: 
- `write_next_section()`: `LongWriterOutput` object (structured output)
- `write_report()`: Complete markdown report string

**Purpose**: Iteratively writes report sections with proper citations and reference management

**File Writing**: ❌ **NO** - Returns string only

**Key Features**:
- Writes sections iteratively
- Reformats and deduplicates references
- Adjusts heading levels
- Aggregates references across sections

---

### 3. ProofreaderAgent
**File**: `src/agents/proofreader.py`

**Method**: `async def proofread(query, report_draft) -> str`

**Returns**: Final polished markdown report string

**Purpose**: Proofreads and finalizes report drafts

**File Writing**: ❌ **NO** - Returns string only

**Key Features**:
- Combines sections
- Removes duplicates
- Adds summary
- Preserves references
- Polishes wording

---

### 4. ReportAgent
**File**: `src/agents/report_agent.py`

**Method**: `async def run(messages, thread, **kwargs) -> AgentRunResponse`

**Returns**: `AgentRunResponse` with markdown text in `messages[0].text`

**Purpose**: Generates structured scientific reports from evidence and hypotheses

**File Writing**: ❌ **NO** - Returns `AgentRunResponse` object

**Key Features**:
- Uses structured `ResearchReport` model
- Validates citations
- Returns markdown via `report.to_markdown()`

---

## File Writing Operations Found

### Temporary File Writing (Not Reports)

1. **ImageOCRService** (`src/services/image_ocr.py`)
   - `_save_image_temp(image) -> str`
   - Saves temporary images for OCR processing
   - Returns temp file path

2. **STTService** (`src/services/stt_gradio.py`)
   - `_save_audio_temp(audio_array, sample_rate) -> str`
   - Saves temporary audio files for transcription
   - Returns temp file path

---

## Where Reports Are Used

### Graph Orchestrator
**File**: `src/orchestrator/graph_orchestrator.py`

- Line 642: `final_report = await long_writer_agent.write_report(...)`
- Returns string result, stored in graph context
- Final result passed through `AgentEvent` with `message` field

### Research Flows
**File**: `src/orchestrator/research_flow.py`

- `IterativeResearchFlow._create_final_report()`: Calls `writer_agent.write_report()`
- `DeepResearchFlow._create_final_report()`: Calls `long_writer_agent.write_report()`
- Both return strings

---

## Integration Points for File Writing

To add file writing capability, you would need to:

1. **After report generation**: Save the returned string to a file
2. **In graph orchestrator**: After `write_report()`, save to file and include path in result
3. **In research flows**: After `_create_final_report()`, save to file

### Example Implementation Pattern

```python
import tempfile
from pathlib import Path

# After report generation
report_content = await writer_agent.write_report(...)

# Save to file
output_dir = Path("/tmp/reports")  # or configurable
output_dir.mkdir(exist_ok=True)
file_path = output_dir / f"report_{timestamp}.md"

with open(file_path, "w", encoding="utf-8") as f:
    f.write(report_content)

# Return both content and file path
return {
    "message": "Report generated successfully",
    "file": str(file_path)
}
```

---

## Recommendations

1. **Add file writing utility**: Create a helper function to save reports to files
2. **Make it optional**: Add configuration flag to enable/disable file saving
3. **Use temp directory**: Save to temp directory by default, allow custom path
4. **Include in graph results**: Modify graph orchestrator to optionally save and return file paths
5. **Support multiple formats**: Consider saving as both `.md` and potentially `.pdf` or `.html`

---

## Current State

✅ **Report Generation**: Fully implemented  
❌ **File Writing**: Not implemented  
✅ **File Output Integration**: Recently added (see previous work on `event_to_chat_message`)  

The infrastructure to handle file outputs in Gradio is in place, but the agents themselves do not yet write files. They would need to be enhanced or wrapped to add file writing capability.




