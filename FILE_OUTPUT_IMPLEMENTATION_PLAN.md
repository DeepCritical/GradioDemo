# File Output Implementation Plan

## Overview

This plan implements file writing and return functionality for report-writing agents, enabling reports to be saved as files and returned through the Gradio ChatInterface.

## Current State Analysis

✅ **Report Generation**: All agents generate markdown strings  
✅ **File Output Integration**: `event_to_chat_message()` supports file paths  
✅ **Graph Orchestrator**: Can handle file paths in results  
❌ **File Writing**: No agents write files to disk  
❌ **File Service**: No utility service for saving reports  

---

## Implementation Plan

### PROJECT 1: File Writing Service
**Goal**: Create a reusable service for saving reports to files

#### Activity 1.1: Create Report File Service
**File**: `src/services/report_file_service.py` (NEW)

**Tasks**:
1. Create `ReportFileService` class
2. Implement `save_report()` method
   - Accepts: report content (str), filename (optional), output_dir (optional)
   - Returns: file path (str)
   - Uses temp directory by default
   - Supports custom output directory
   - Handles file naming with timestamps
3. Implement `save_report_multiple_formats()` method
   - Save as .md (always)
   - Optionally save as .html, .pdf (future)
4. Add configuration support
   - Read from settings
   - Enable/disable file saving
   - Configurable output directory
5. Add error handling and logging
6. Add file cleanup utilities (optional)

**Line-level subtasks**:
- Line 1-20: Imports and class definition
- Line 21-40: `__init__()` method with settings
- Line 41-80: `save_report()` method
  - Line 41-50: Input validation
  - Line 51-60: Directory creation
  - Line 61-70: File writing
  - Line 71-80: Error handling
- Line 81-100: `save_report_multiple_formats()` method
- Line 101-120: Helper methods (filename generation, cleanup)

---

### PROJECT 2: Configuration Updates
**Goal**: Add settings for file output functionality

#### Activity 2.1: Update Settings Model
**File**: `src/utils/config.py`

**Tasks**:
1. Add `save_reports_to_file: bool` field (default: True)
2. Add `report_output_directory: str | None` field (default: None, uses temp)
3. Add `report_file_format: Literal["md", "md_html", "md_pdf"]` field (default: "md")
4. Add `report_filename_template: str` field (default: "report_{timestamp}_{query_hash}.md")

**Line-level subtasks**:
- Line 166-170: Add `save_reports_to_file` field after TTS config
- Line 171-175: Add `report_output_directory` field
- Line 176-180: Add `report_file_format` field
- Line 181-185: Add `report_filename_template` field

---

### PROJECT 3: Graph Orchestrator Integration
**Goal**: Integrate file writing into graph execution

#### Activity 3.1: Update Graph Orchestrator
**File**: `src/orchestrator/graph_orchestrator.py`

**Tasks**:
1. Import `ReportFileService` at top
2. Initialize service in `__init__()` (optional, can be lazy)
3. Modify `_execute_agent_node()` for synthesizer node
   - After `long_writer_agent.write_report()`, save to file
   - Return dict with `{"message": report, "file": file_path}`
4. Update final event generation to handle file paths
   - Already implemented, verify it works correctly

**Line-level subtasks**:
- Line 1-35: Add import for `ReportFileService`
- Line 119-148: Update `__init__()` to accept optional file service
- Line 589-650: Modify `_execute_agent_node()` synthesizer handling
  - Line 642-645: After `write_report()`, add file saving
  - Line 646-650: Return dict with file path
- Line 534-564: Verify final event generation handles file paths (already done)

---

### PROJECT 4: Research Flow Integration
**Goal**: Integrate file writing into research flows

#### Activity 4.1: Update IterativeResearchFlow
**File**: `src/orchestrator/research_flow.py`

**Tasks**:
1. Import `ReportFileService` at top
2. Add optional file service to `__init__()`
3. Modify `_create_final_report()` method
   - After `writer_agent.write_report()`, save to file if enabled
   - Return string (backward compatible) OR dict with file path

**Line-level subtasks**:
- Line 1-50: Add import for `ReportFileService`
- Line 48-120: Update `__init__()` to accept optional file service
- Line 622-667: Modify `_create_final_report()` method
  - Line 647-652: After `write_report()`, add file saving
  - Line 653-667: Return report string (keep backward compatible for now)

#### Activity 4.2: Update DeepResearchFlow
**File**: `src/orchestrator/research_flow.py`

**Tasks**:
1. Add optional file service to `__init__()` (if not already)
2. Modify `_create_final_report()` method
   - After `long_writer_agent.write_report()` or `proofreader_agent.proofread()`, save to file
   - Return string (backward compatible) OR dict with file path

**Line-level subtasks**:
- Line 670-750: Update `DeepResearchFlow.__init__()` to accept optional file service
- Line 954-1005: Modify `_create_final_report()` method
  - Line 979-983: After `write_report()`, add file saving
  - Line 984-989: After `proofread()`, add file saving
  - Line 990-1005: Return report string (keep backward compatible)

---

### PROJECT 5: Agent Factory Integration
**Goal**: Make file service available to agents if needed

#### Activity 5.1: Update Agent Factory (Optional)
**File**: `src/agent_factory/agents.py`

**Tasks**:
1. Add optional file service parameter to agent creation functions (if needed)
2. Pass file service to agents that need it (currently not needed, agents return strings)

**Line-level subtasks**:
- Not required - agents return strings, file writing happens at orchestrator level

---

### PROJECT 6: Testing & Validation
**Goal**: Ensure file output works end-to-end

#### Activity 6.1: Unit Tests
**File**: `tests/unit/services/test_report_file_service.py` (NEW)

**Tasks**:
1. Test `save_report()` with default settings
2. Test `save_report()` with custom directory
3. Test `save_report()` with custom filename
4. Test error handling (permission errors, disk full, etc.)
5. Test file cleanup

**Line-level subtasks**:
- Line 1-30: Test fixtures and setup
- Line 31-60: Test basic save functionality
- Line 61-90: Test custom directory
- Line 91-120: Test error handling

#### Activity 6.2: Integration Tests
**File**: `tests/integration/test_file_output_integration.py` (NEW)

**Tasks**:
1. Test graph orchestrator with file output
2. Test research flows with file output
3. Test Gradio ChatInterface receives file paths
4. Test file download in Gradio UI

**Line-level subtasks**:
- Line 1-40: Test setup with mock orchestrator
- Line 41-80: Test file generation in graph execution
- Line 81-120: Test file paths in AgentEvent
- Line 121-160: Test Gradio message conversion

---

## Implementation Order

1. **PROJECT 2** (Configuration) - Foundation
2. **PROJECT 1** (File Service) - Core functionality
3. **PROJECT 3** (Graph Orchestrator) - Primary integration point
4. **PROJECT 4** (Research Flows) - Secondary integration points
5. **PROJECT 6** (Testing) - Validation
6. **PROJECT 5** (Agent Factory) - Not needed, skip

---

## File Changes Summary

### New Files
- `src/services/report_file_service.py` - File writing service
- `tests/unit/services/test_report_file_service.py` - Unit tests
- `tests/integration/test_file_output_integration.py` - Integration tests

### Modified Files
- `src/utils/config.py` - Add file output settings
- `src/orchestrator/graph_orchestrator.py` - Add file saving after report generation
- `src/orchestrator/research_flow.py` - Add file saving in both flows

---

## Gradio Integration Notes

According to Gradio ChatInterface documentation:
- File paths in chat message content are automatically converted to download links
- Markdown links like `[Download: filename](file_path)` work
- Files must be accessible from the Gradio server
- Temp files are fine as long as they exist during the session

Current implementation in `event_to_chat_message()` already handles this correctly.

---

## Success Criteria

✅ Reports are saved to files when generated  
✅ File paths are included in AgentEvent data  
✅ File paths appear as download links in Gradio ChatInterface  
✅ File saving is configurable (can be disabled)  
✅ Backward compatible (existing code still works)  
✅ Error handling prevents crashes if file writing fails  



