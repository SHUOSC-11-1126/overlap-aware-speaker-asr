# Speaker Profile Multi-signal Diagnostic

This generated note compares text-profile and audio-profile proxy signals. It remains experimental/frontier and does not claim speaker identification.

| case_id | hypothesis_source | text_best_alignment | audio_best_alignment | text_confidence_gap | audio_confidence_gap | alignment_agreement | audio_support_level | combined_signal_status | recommended_next_step | result_label | observation |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| NoOverlap | separated_whisper | swapped | swapped | 0.422118 | 0.000012 | agree | weak_support | text_swapped_audio_weak | Advance only to a narrow embedding baseline; attribution claims remain blocked. | experimental/frontier | Multi-signal speaker-risk diagnostic only; this is not speaker identification. |
| LightOverlap | separated_whisper_cleaned | swapped | swapped | 0.418882 | 0.000012 | agree | weak_support | text_swapped_audio_weak | Advance only to a narrow embedding baseline; attribution claims remain blocked. | experimental/frontier | Multi-signal speaker-risk diagnostic only; this is not speaker identification. |
| MidOverlap | separated_whisper_cleaned | swapped | swapped | 0.406764 | 0.000013 | agree | weak_support | text_swapped_audio_weak | Advance only to a narrow embedding baseline; attribution claims remain blocked. | experimental/frontier | Multi-signal speaker-risk diagnostic only; this is not speaker identification. |
| HeavyOverlap | separated_whisper_cleaned | swapped | swapped | 0.411129 | 0.000014 | agree | weak_support | text_swapped_audio_weak | Advance only to a narrow embedding baseline; attribution claims remain blocked. | experimental/frontier | Multi-signal speaker-risk diagnostic only; this is not speaker identification. |
| OppositeOverlap | separated_whisper_cleaned | swapped | swapped | 0.406764 | 0.000015 | agree | weak_support | text_swapped_audio_weak | Advance only to a narrow embedding baseline; attribution claims remain blocked. | experimental/frontier | Multi-signal speaker-risk diagnostic only; this is not speaker identification. |
