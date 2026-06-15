# Whisper Config Sweep

- `base_beam1`: n=`10`, avg mixed CER=`0.747664`, status=`complete`
- `base_beam5`: n=`10`, avg mixed CER=`0.77802`, status=`complete`
- `base_vad`: n=`10`, avg mixed CER=`0.779231`, status=`complete`
- `base_prompt`: n=`10`, avg mixed CER=`1.290242`, status=`complete`
- `small_beam5_partial`: n=`0`, avg mixed CER=``, status=`partial`

Sweep uses mixed audio only to test whether the Stage 24 `base` configuration is an ASR bottleneck. It is not a full route comparison.
