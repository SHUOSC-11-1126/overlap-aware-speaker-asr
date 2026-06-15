# Whisper Environment Diagnosis

- Python: `/Users/ark/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`
- Python version: `3.12.13`
- ffmpeg: `missing`
- torch: `True` version `2.12.0`
- faster-whisper: `True` version `1.2.1`
- openai-whisper: `False` version ``
- soundfile: `True` version `0.14.0`
- selected backend: `faster-whisper`

## Missing Or Limitations

- system ffmpeg command is not available; faster-whisper can still use PyAV, openai-whisper usually needs ffmpeg
