# MeetEval cpWER Official Execution Tokenization Diagnostic

This generated diagnostic identifies why official MeetEval cpWER may drift from bridge-lite on Chinese gold cases. It remains experimental/frontier and does not claim benchmark completion.

Summary: `5/5` cases report `no_whitespace_word_tokenization` root cause.

| case_id | speaker_count | raw_token_count_per_speaker | character_token_count_per_speaker | root_cause | diagnostic_status | diagnostic_note |
| --- | ---: | ---: | ---: | --- | --- | --- |
| NoOverlap | 2 | 1.0 | 139.0 | no_whitespace_word_tokenization | root_cause_identified | MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; character-spaced tokenization is required for CJK alignment with bridge-lite. |
| LightOverlap | 2 | 1.0 | 140.0 | no_whitespace_word_tokenization | root_cause_identified | MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; character-spaced tokenization is required for CJK alignment with bridge-lite. |
| MidOverlap | 2 | 1.0 | 142.5 | no_whitespace_word_tokenization | root_cause_identified | MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; character-spaced tokenization is required for CJK alignment with bridge-lite. |
| HeavyOverlap | 2 | 1.0 | 141.0 | no_whitespace_word_tokenization | root_cause_identified | MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; character-spaced tokenization is required for CJK alignment with bridge-lite. |
| OppositeOverlap | 2 | 1.0 | 138.0 | no_whitespace_word_tokenization | root_cause_identified | MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; character-spaced tokenization is required for CJK alignment with bridge-lite. |
