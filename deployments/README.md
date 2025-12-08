# Deployments

This directory contains infrastructure deployment scripts for DeepCritical services.

## Modal Deployments

### TTS Service (`modal_tts.py`)

Deploys the Kokoro TTS (Text-to-Speech) function to Modal's GPU infrastructure.

**Deploy:**
```bash
modal deploy deployments/modal_tts.py
```

**Features:**
- Kokoro 82M TTS model
- GPU-accelerated (T4)
- Voice options: af_heart, af_bella, am_michael, etc.
- Configurable speech speed

**Requirements:**
- Modal account and credentials (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` in `.env`)
- GPU quota on Modal

**After Deployment:**
The function will be available at:
- App: `deepcritical-tts`
- Function: `kokoro_tts_function`

The main application (`src/services/tts_modal.py`) will call this deployed function.

---

## Adding New Deployments

When adding new deployment scripts:

1. Create a new file: `deployments/<service_name>.py`
2. Use Modal's app pattern:
   ```python
   import modal
   app = modal.App("deepcritical-<service-name>")
   ```
3. Document in this README
4. Test deployment: `modal deploy deployments/<service_name>.py`
