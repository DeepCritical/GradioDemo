# Multimodal Settings & File Rendering - Implementation Plan

## Executive Summary

This document provides a comprehensive analysis of the current settings implementation, multimodal input handling, and file rendering in `src/app.py`, along with a detailed implementation plan to improve the user experience.

## 1. Current Settings Analysis

### 1.1 Settings Structure in `src/app.py`

**Current Implementation (Lines 741-887):**

1. **Sidebar Structure:**
   - Authentication section (lines 745-750)
   - About section (lines 752-764)
   - Settings section (lines 767-850):
     - Research Configuration Accordion (lines 771-796):
       - `mode_radio`: Orchestrator mode selector
       - `graph_mode_radio`: Graph research mode selector
       - `use_graph_checkbox`: Graph execution toggle
     - Audio Output Accordion (lines 798-850):
       - `enable_audio_output_checkbox`: TTS enable/disable
       - `tts_voice_dropdown`: Voice selection
       - `tts_speed_slider`: Speech speed control
       - `tts_gpu_dropdown`: GPU type (non-interactive, visible only if Modal available)

2. **Hidden Components (Lines 852-865):**
   - `hf_model_dropdown`: Hidden Textbox for model selection
   - `hf_provider_dropdown`: Hidden Textbox for provider selection

3. **Main Area Components (Lines 867-887):**
   - `audio_output`: Audio output component (visible based on `settings.enable_audio_output`)
   - Visibility update function for TTS components

### 1.2 Settings Flow

**Settings → Function Parameters:**
- Settings from sidebar accordions are passed via `additional_inputs` to `research_agent()` function
- Hidden textboxes are also passed but use empty strings (converted to None)
- OAuth token/profile are automatically passed by Gradio

**Function Signature (Lines 535-546):**
```python
async def research_agent(
    message: str | MultimodalPostprocess,
    history: list[dict[str, Any]],
    mode: str = "simple",
    hf_model: str | None = None,
    hf_provider: str | None = None,
    graph_mode: str = "auto",
    use_graph: bool = True,
    tts_voice: str = "af_heart",
    tts_speed: float = 1.0,
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
)
```

### 1.3 Issues Identified

1. **Settings Organization:**
   - Audio output component is in main area, not sidebar
   - Hidden components (hf_model, hf_provider) should be visible or removed
   - No image input enable/disable setting (only audio input has this)

2. **Visibility:**
   - Audio output visibility is controlled by checkbox, but component placement is suboptimal
   - TTS settings visibility is controlled by checkbox change event

3. **Configuration Gaps:**
   - No `enable_image_input` setting in config (only `enable_audio_input` exists)
   - Image processing always happens if files are present (line 626 comment says "not just when enable_image_input is True" but setting doesn't exist)

## 2. Multimodal Input Analysis

### 2.1 Current Implementation

**ChatInterface Configuration (Line 892-958):**
- `multimodal=True`: Enables MultimodalTextbox component
- MultimodalTextbox automatically provides:
  - Text input
  - Image upload button
  - Audio recording button
  - File upload support

**Input Processing (Lines 613-642):**
- Message can be `str` or `MultimodalPostprocess` (dict format)
- MultimodalPostprocess format: `{"text": str, "files": list[FileData], "audio": tuple | None}`
- Processing happens in `research_agent()` function:
  - Extracts text, files, and audio from message
  - Calls `multimodal_service.process_multimodal_input()`
  - Condition: `if files or (audio_input_data is not None and settings.enable_audio_input)`

**Multimodal Service (src/services/multimodal_processing.py):**
- Processes audio input if `settings.enable_audio_input` is True
- Processes image files (no enable/disable check - always processes if files present)
- Extracts text from images using OCR service
- Transcribes audio using STT service

### 2.2 Gradio Documentation Findings

**MultimodalTextbox (ChatInterface with multimodal=True):**
- Automatically provides image and audio input capabilities
- Inputs are always visible when ChatInterface is rendered
- No explicit visibility control needed - it's part of the textbox component
- Files are handled via `files` array in MultimodalPostprocess
- Audio recording is handled via `audio` tuple in MultimodalPostprocess

**Reference Implementation Pattern:**
```python
gr.ChatInterface(
    fn=chat_function,
    multimodal=True,  # Enables image/audio inputs
    # ... other parameters
)
```

### 2.3 Issues Identified

1. **Visibility:**
   - Multimodal inputs ARE always visible (they're part of MultimodalTextbox)
   - No explicit control needed - this is working correctly
   - However, users may not realize image/audio inputs are available

2. **Configuration:**
   - No `enable_image_input` setting to disable image processing
   - Image processing always happens if files are present
   - Audio processing respects `settings.enable_audio_input`

3. **User Experience:**
   - No visual indication that multimodal inputs are available
   - Description mentions "🎤 Multimodal Support" but could be more prominent

## 3. File Rendering Analysis

### 3.1 Current Implementation

**File Detection (Lines 168-195):**
- `_is_file_path()`: Checks if text looks like a file path
- Checks for file extensions and path separators

**File Rendering in Events (Lines 242-298):**
- For "complete" events, checks `event.data` for "files" or "file" keys
- Validates files exist using `os.path.exists()`
- Formats files as markdown download links: `📎 [Download: filename](filepath)`
- Stores files in metadata for potential future use

**File Links Format:**
```python
file_links = "\n\n".join([
    f"📎 [Download: {_get_file_name(f)}]({f})" 
    for f in valid_files
])
result["content"] = f"{content}\n\n{file_links}"
```

### 3.2 Issues Identified

1. **Rendering Method:**
   - Uses markdown links in content string
   - May not work reliably in all Gradio versions
   - Better approach: Use Gradio's native file components or File component

2. **File Validation:**
   - Only checks if file exists
   - Doesn't validate file type or size
   - No error handling for inaccessible files

3. **User Experience:**
   - Files appear as text links, not as proper file components
   - No preview for images/PDFs
   - No file size information

## 4. Implementation Plan

### Activity 1: Settings Reorganization

**Goal:** Move all settings to sidebar with better organization

**File:** `src/app.py`

**Tasks:**

1. **Move Audio Output Component to Sidebar (Lines 867-887)**
   - Move `audio_output` component into sidebar
   - Place it in Audio Output accordion or create separate section
   - Update visibility logic to work within sidebar

2. **Add Image Input Settings (New)**
   - Add `enable_image_input` checkbox to sidebar
   - Create "Image Input" accordion or add to existing "Multimodal Input" accordion
   - Update config to include `enable_image_input` setting

3. **Organize Settings Accordions**
   - Research Configuration (existing)
   - Multimodal Input (new - combine image and audio input settings)
   - Audio Output (existing - move component here)
   - Model Configuration (new - for hf_model, hf_provider if we make them visible)

**Subtasks:**
- [ ] Line 867-871: Move `audio_output` component definition into sidebar
- [ ] Line 873-887: Update visibility update function to work with sidebar placement
- [ ] Line 798-850: Reorganize Audio Output accordion to include audio_output component
- [ ] Line 767-796: Keep Research Configuration as-is
- [ ] After line 796: Add new "Multimodal Input" accordion with enable_image_input and enable_audio_input checkboxes
- [ ] Line 852-865: Consider making hf_model and hf_provider visible or remove them

### Activity 2: Multimodal Input Visibility

**Goal:** Ensure multimodal inputs are always visible and well-documented

**File:** `src/app.py`

**Tasks:**

1. **Verify Multimodal Inputs Are Visible**
   - Confirm `multimodal=True` in ChatInterface (already done - line 894)
   - Add visual indicators in description
   - Add tooltips or help text

2. **Add Image Input Configuration**
   - Add `enable_image_input` to config (src/utils/config.py)
   - Update multimodal processing to respect this setting
   - Add UI control in sidebar

**Subtasks:**
- [ ] Line 894: Verify `multimodal=True` is set (already correct)
- [ ] Line 908: Enhance description to highlight multimodal capabilities
- [ ] src/utils/config.py: Add `enable_image_input: bool = Field(default=True, ...)`
- [ ] src/services/multimodal_processing.py: Add check for `settings.enable_image_input` before processing images
- [ ] src/app.py: Add enable_image_input checkbox to sidebar

### Activity 3: File Rendering Improvements

**Goal:** Improve file rendering using proper Gradio components

**File:** `src/app.py`

**Tasks:**

1. **Improve File Rendering Method**
   - Use Gradio File component or proper file handling
   - Add file previews for images
   - Show file size and type information

2. **Enhance File Validation**
   - Validate file types
   - Check file accessibility
   - Handle errors gracefully

**Subtasks:**
- [ ] Line 280-296: Replace markdown link approach with proper file component rendering
- [ ] Line 168-195: Enhance `_is_file_path()` to validate file types
- [ ] Line 242-298: Update `event_to_chat_message()` to use Gradio File components
- [ ] Add file preview functionality for images
- [ ] Add error handling for inaccessible files

### Activity 4: Configuration Updates

**Goal:** Add missing configuration settings

**File:** `src/utils/config.py`

**Tasks:**

1. **Add Image Input Setting**
   - Add `enable_image_input` field
   - Add `ocr_api_url` field if missing
   - Add property methods for availability checks

**Subtasks:**
- [ ] After line 147: Add `enable_image_input: bool = Field(default=True, description="Enable image input (OCR) in multimodal interface")`
- [ ] Check if `ocr_api_url` exists (should be in config)
- [ ] Add `image_ocr_available` property if missing

### Activity 5: Multimodal Service Updates

**Goal:** Respect image input enable/disable setting

**File:** `src/services/multimodal_processing.py`

**Tasks:**

1. **Add Image Input Check**
   - Check `settings.enable_image_input` before processing images
   - Log when image processing is skipped due to setting

**Subtasks:**
- [ ] Line 66-77: Add check for `settings.enable_image_input` before processing image files
- [ ] Add logging when image processing is skipped

## 5. Detailed File-Level Tasks

### File: `src/app.py`

**Line-Level Subtasks:**

1. **Lines 741-850: Sidebar Reorganization**
   - [ ] 741-765: Keep authentication and about sections
   - [ ] 767-796: Keep Research Configuration accordion
   - [ ] 797: Add new "Multimodal Input" accordion after Research Configuration
   - [ ] 798-850: Reorganize Audio Output accordion, move audio_output component here
   - [ ] 852-865: Review hidden components - make visible or remove

2. **Lines 867-887: Audio Output Component**
   - [ ] 867-871: Move `audio_output` definition into sidebar (Audio Output accordion)
   - [ ] 873-887: Update visibility function to work with sidebar placement

3. **Lines 892-958: ChatInterface Configuration**
   - [ ] 894: Verify `multimodal=True` (already correct)
   - [ ] 908: Enhance description with multimodal capabilities
   - [ ] 946-956: Review `additional_inputs` - ensure all settings are included

4. **Lines 242-298: File Rendering**
   - [ ] 280-296: Replace markdown links with proper file component rendering
   - [ ] Add file preview for images
   - [ ] Add file size/type information

5. **Lines 613-642: Multimodal Input Processing**
   - [ ] 626: Update condition to check `settings.enable_image_input` for files
   - [ ] Add logging for when image processing is skipped

### File: `src/utils/config.py`

**Line-Level Subtasks:**

1. **Lines 143-180: Audio/Image Configuration**
   - [ ] 144-147: `enable_audio_input` exists (keep as-is)
   - [ ] After 147: Add `enable_image_input: bool = Field(default=True, description="Enable image input (OCR) in multimodal interface")`
   - [ ] Check if `ocr_api_url` exists (add if missing)
   - [ ] Add `image_ocr_available` property method

### File: `src/services/multimodal_processing.py`

**Line-Level Subtasks:**

1. **Lines 65-77: Image Processing**
   - [ ] 66: Add check: `if files and settings.enable_image_input:`
   - [ ] 71-77: Keep image processing logic inside the new condition
   - [ ] Add logging when image processing is skipped

## 6. Testing Checklist

- [ ] Verify all settings are in sidebar
- [ ] Test multimodal inputs (image upload, audio recording)
- [ ] Test file rendering (markdown, PDF, images)
- [ ] Test enable/disable toggles for image and audio inputs
- [ ] Test audio output generation and display
- [ ] Test file download links
- [ ] Verify settings persist across chat sessions
- [ ] Test on different screen sizes (responsive design)

## 7. Implementation Order

1. **Phase 1: Configuration** (Foundation)
   - Add `enable_image_input` to config
   - Update multimodal service to respect setting

2. **Phase 2: Settings Reorganization** (UI)
   - Move audio output to sidebar
   - Add image input settings to sidebar
   - Organize accordions

3. **Phase 3: File Rendering** (Enhancement)
   - Improve file rendering method
   - Add file previews
   - Enhance validation

4. **Phase 4: Testing & Refinement** (Quality)
   - Test all functionality
   - Fix any issues
   - Refine UI/UX

## 8. Success Criteria

- ✅ All settings are in sidebar
- ✅ Multimodal inputs are always visible and functional
- ✅ Files are rendered properly with previews
- ✅ Image and audio input can be enabled/disabled
- ✅ Settings are well-organized and intuitive
- ✅ No regressions in existing functionality




