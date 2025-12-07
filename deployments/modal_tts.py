"""Deploy Kokoro TTS function to Modal.

This script deploys the TTS function to Modal so it can be called
from the main DeepCritical application.

Usage:
    modal deploy deploy_modal_tts.py

After deployment, the function will be available at:
    App: deepcritical-tts
    Function: kokoro_tts_function
"""

import modal
import numpy as np

# Create Modal app
app = modal.App("deepcritical-tts")

# Define Kokoro TTS dependencies
KOKORO_DEPENDENCIES = [
    "torch>=2.0.0",
    "transformers>=4.30.0",
    "numpy<2.0",
]

# Create Modal image with Kokoro
tts_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")  # Install git first for pip install from github
    .pip_install(*KOKORO_DEPENDENCIES)
    .pip_install("git+https://github.com/hexgrad/kokoro.git")
)


@app.function(
    image=tts_image,
    gpu="T4",
    timeout=60,
)
def kokoro_tts_function(text: str, voice: str, speed: float) -> tuple[int, np.ndarray]:
    """Modal GPU function for Kokoro TTS.

    This function runs on Modal's GPU infrastructure.
    Based on: https://huggingface.co/spaces/hexgrad/Kokoro-TTS

    Args:
        text: Text to synthesize
        voice: Voice ID (e.g., af_heart, af_bella, am_michael)
        speed: Speech speed multiplier (0.5-2.0)

    Returns:
        Tuple of (sample_rate, audio_array)
    """
    import numpy as np

    try:
        import torch
        from kokoro import KModel, KPipeline

        # Initialize model (cached on GPU)
        model = KModel().to("cuda").eval()
        pipeline = KPipeline(lang_code=voice[0])
        pack = pipeline.load_voice(voice)

        # Generate audio - accumulate all chunks
        audio_chunks = []
        for _, ps, _ in pipeline(text, voice, speed):
            ref_s = pack[len(ps) - 1]
            audio = model(ps, ref_s, speed)
            audio_chunks.append(audio.numpy())

        # Concatenate all audio chunks
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            return (24000, full_audio)

        # If no audio generated, return empty
        return (24000, np.zeros(1, dtype=np.float32))

    except ImportError as e:
        raise RuntimeError(
            f"Kokoro not installed: {e}. "
            "Install with: pip install git+https://github.com/hexgrad/kokoro.git"
        ) from e
    except Exception as e:
        raise RuntimeError(f"TTS synthesis failed: {e}") from e


# Optional: Add a test entrypoint
@app.local_entrypoint()
def test():
    """Test the TTS function."""
    print("Testing Modal TTS function...")
    sample_rate, audio = kokoro_tts_function.remote(
        "Hello, this is a test.",
        "af_heart",
        1.0
    )
    print(f"Generated audio: {sample_rate}Hz, shape={audio.shape}")
    print("✓ TTS function works!")
