# TTS Modal GPU Implementation

## Overview

The TTS (Text-to-Speech) service uses Kokoro 82M model running on Modal's GPU infrastructure. This document describes the implementation details and configuration.

## Implementation Details

### Modal GPU Function Pattern

The implementation follows Modal's recommended pattern for GPU functions:

1. **Module-Level Function Definition**: Modal functions must be defined at module level and attached to an app instance
2. **Lazy Initialization**: The function is set up on first use via `_setup_modal_function()`
3. **GPU Configuration**: GPU type is set at function definition time (requires app restart to change)

### Key Files

- `src/services/tts_modal.py` - Modal GPU executor for Kokoro TTS
- `src/services/audio_processing.py` - Unified audio service wrapper
- `src/utils/config.py` - Configuration settings
- `src/app.py` - UI integration with settings accordion

### Configuration Options

All TTS configuration is available in `src/utils/config.py`:

```python
tts_model: str = "hexgrad/Kokoro-82M"  # Model ID
tts_voice: str = "af_heart"  # Voice ID
tts_speed: float = 1.0  # Speed multiplier (0.5-2.0)
tts_gpu: str = "T4"  # GPU type (T4, A10, A100, etc.)
tts_timeout: int = 60  # Timeout in seconds
enable_audio_output: bool = True  # Enable/disable TTS
```

### UI Configuration

TTS settings are available in the Settings accordion:

- **Voice Dropdown**: Select from 20+ Kokoro voices (af_heart, af_bella, am_michael, etc.)
- **Speed Slider**: Adjust speech speed (0.5x to 2.0x)
- **GPU Dropdown**: Select GPU type (T4, A10, A100, L4, L40S) - visible only if Modal credentials configured
- **Enable Audio Output**: Toggle TTS generation

### Modal Function Implementation

The Modal GPU function is defined as:

```python
@app.function(
    image=tts_image,  # Image with Kokoro dependencies
    gpu="T4",  # GPU type (from settings.tts_gpu)
    timeout=60,  # Timeout (from settings.tts_timeout)
)
def kokoro_tts_function(text: str, voice: str, speed: float) -> tuple[int, np.ndarray]:
    """Modal GPU function for Kokoro TTS."""
    from kokoro import KModel, KPipeline
    import torch
    
    model = KModel().to("cuda").eval()
    pipeline = KPipeline(lang_code=voice[0])
    pack = pipeline.load_voice(voice)
    
    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps) - 1]
        audio = model(ps, ref_s, speed)
        return (24000, audio.numpy())
```

### Usage Flow

1. User submits query with audio output enabled
2. Research agent processes query and generates text response
3. `AudioService.generate_audio_output()` is called with:
   - Response text
   - Voice (from UI dropdown or settings default)
   - Speed (from UI slider or settings default)
4. `TTSService.synthesize_async()` calls Modal GPU function
5. Modal executes Kokoro TTS on GPU
6. Audio tuple `(sample_rate, audio_array)` is returned
7. Audio is displayed in Gradio Audio component

### Dependencies

Installed via `uv add --optional`:
- `gradio-client>=1.0.0` - For STT/OCR API calls
- `soundfile>=0.12.0` - For audio file I/O
- `Pillow>=10.0.0` - For image processing

Kokoro is installed in Modal image from source:
- `git+https://github.com/hexgrad/kokoro.git`

### GPU Types

Modal supports various GPU types:
- **T4**: Cheapest, good for testing (default)
- **A10**: Good balance of cost/performance
- **A100**: Fastest, most expensive
- **L4**: NVIDIA L4 GPU
- **L40S**: NVIDIA L40S GPU

**Note**: GPU type is set at function definition time. Changes to `settings.tts_gpu` require app restart.

### Error Handling

- If Modal credentials not configured: TTS service unavailable (graceful degradation)
- If Kokoro import fails: ConfigurationError raised
- If synthesis fails: Returns None, logs warning, continues without audio
- If GPU unavailable: Modal will queue or fail with clear error message

### Configuration Connection

1. **Settings → Implementation**: `settings.tts_voice`, `settings.tts_speed` used as defaults
2. **UI → Implementation**: UI dropdowns/sliders passed to `research_agent()` function
3. **Implementation → Modal**: Voice and speed passed to Modal GPU function
4. **GPU Configuration**: Set at function definition time (requires restart to change)

### Testing

To test TTS:
1. Ensure Modal credentials configured (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`)
2. Enable audio output in settings
3. Submit a query
4. Check audio output component for generated speech

### References

- [Kokoro TTS Space](https://huggingface.co/spaces/hexgrad/Kokoro-TTS) - Reference implementation
- [Modal GPU Documentation](https://modal.com/docs/guide/gpu) - Modal GPU usage
- [Kokoro GitHub](https://github.com/hexgrad/kokoro) - Source code










