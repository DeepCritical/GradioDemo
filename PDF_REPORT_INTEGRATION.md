# PDF Report Generation Integration

## Summary

Integrated PDF generation functionality into the report file service using utilities from `folder/utils copy`. Reports can now be automatically converted to PDF format as a final step.

## Changes Made

### 1. Added PDF Conversion Utilities

**Files Created:**
- `src/utils/md_to_pdf.py` - Markdown to PDF conversion utility
- `src/utils/markdown.css` - CSS styling for PDF output

**Features:**
- Uses `md2pdf` library for conversion
- Includes error handling and graceful fallback
- Supports custom CSS styling
- Logs conversion status

### 2. Enhanced ReportFileService

**File:** `src/services/report_file_service.py`

**Changes:**
- Added `_save_pdf()` method to generate PDF from markdown
- Updated `save_report_multiple_formats()` to implement PDF generation
- PDF is generated when `report_file_format` is set to `"md_pdf"`
- Both markdown and PDF files are saved and returned

**Method Signature:**
```python
def _save_pdf(
    self,
    report_content: str,
    query: str | None = None,
) -> str:
    """Save report as PDF. Returns path to PDF file."""
```

### 3. Updated Graph Orchestrator

**File:** `src/orchestrator/graph_orchestrator.py`

**Changes:**
- Updated synthesizer node to use `save_report_multiple_formats()`
- Updated writer node to use `save_report_multiple_formats()`
- Both nodes now return PDF paths in result dict when available
- Result includes both `file` (markdown) and `files` (both formats) keys

**Result Format:**
```python
{
    "message": final_report,  # Report content
    "file": "/path/to/report.md",  # Markdown file
    "files": ["/path/to/report.md", "/path/to/report.pdf"]  # Both formats
}
```

## Configuration

PDF generation is controlled by the `report_file_format` setting in `src/utils/config.py`:

```python
report_file_format: Literal["md", "md_html", "md_pdf"] = Field(
    default="md",
    description="File format(s) to save reports in."
)
```

**Options:**
- `"md"` - Save only markdown (default)
- `"md_html"` - Save markdown + HTML (not yet implemented)
- `"md_pdf"` - Save markdown + PDF ✅ **Now implemented**

## Usage

### Enable PDF Generation

Set the environment variable or update settings:
```bash
REPORT_FILE_FORMAT=md_pdf
```

Or in code:
```python
from src.utils.config import settings
settings.report_file_format = "md_pdf"
```

### Dependencies

PDF generation requires the `md2pdf` library:
```bash
pip install md2pdf
```

If `md2pdf` is not installed, the system will:
- Log a warning
- Continue with markdown-only saving
- Not fail the report generation

## File Output

When PDF generation is enabled:
1. Markdown file is always saved first
2. PDF is generated from the markdown content
3. Both file paths are returned in the result
4. Gradio interface can display/download both files

## Error Handling

- If PDF generation fails, markdown file is still saved
- Errors are logged but don't interrupt report generation
- Graceful fallback ensures reports are always available

## Integration Points

PDF generation is automatically triggered when:
1. Graph orchestrator synthesizer node completes
2. Graph orchestrator writer node completes
3. `save_report_multiple_formats()` is called
4. `report_file_format` is set to `"md_pdf"`

## Future Enhancements

- HTML format support (`md_html`)
- Custom PDF templates
- PDF metadata (title, author, keywords)
- PDF compression options
- Batch PDF generation



