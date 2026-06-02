# Technical Implementation Plan for Codex

> Status: Historical document. The current project direction is maintained in docs/technical_implementation_plan_v2.md and docs/project_state.md.

## Project Title

**Overlap-Aware Speaker-Attributed ASR with RAG-Enhanced LLM Correction**

中文题目：

**面向重叠语音的说话人归属转写与 RAG 增强纠错系统**

---

## 0. Project Background

Current local resource directory:

```text
D:\mlproject\project1_xutong
```

This directory contains the original project resources from XuTong’s work, including:

```text
Project.md
xutong_paper.pdf
语音识别模型/whisper.py
语音识别模型/voxtral.py
重叠/chongdie.py
重叠/chongdie2.py
audio_exemple/
```

Our project should not directly copy XuTong’s system. Instead, we will build a focused research-engineering project based on its limitations.

The selected course topic is **Project Topic 1**:

```text
Speaker Diarization
Multi-speaker overlapping speech / cross-speech
LLM + ASR synergy
Based on xutong_paper.pdf
Find limitations / missing components
Propose new method and test it
RAG can be integrated
```

Our project focuses on the key bottleneck:

```text
How to improve ASR and speaker attribution under overlapping speech,
and whether RAG-enhanced LLM correction can reduce transcription,
terminology, and speaker attribution errors.
```

---

# 1. First Step: Create GitHub Repository

## 1.1 Repository Name

Create a new GitHub repository:

```text
overlap-aware-speaker-asr
```

Alternative name:

```text
rag-enhanced-multispeaker-asr
```

Recommended final repository name:

```text
overlap-aware-speaker-asr
```

## 1.2 Initial Git Commands

Run these commands from:

```text
D:\mlproject
```

```bash
mkdir overlap-aware-speaker-asr
cd overlap-aware-speaker-asr
git init
```

Create initial files:

```bash
type nul > README.md
type nul > REPORT.md
type nul > requirements.txt
type nul > .gitignore
```

First commit:

```bash
git add .
git commit -m "init project structure"
```

Then create GitHub repo online and connect remote:

```bash
git remote add origin https://github.com/<YOUR_ORG_OR_USERNAME>/overlap-aware-speaker-asr.git
git branch -M main
git push -u origin main
```

---

# 2. Repository Structure

Create the following project structure:

```text
overlap-aware-speaker-asr/
  README.md
  REPORT.md
  requirements.txt
  .gitignore

  configs/
    config.yaml

  resources/
    mixed_audio/
    separated_audio/
    snippets/
    glossary/
      terms.json
      speaker_profiles.json

  references/
    reference_transcripts.json
    reference_summaries.json

  src/
    __init__.py
    config.py
    audio_manifest.py
    transcribe_whisper.py
    transcribe_funasr.py
    compare_mixed_vs_separated.py
    merge_speaker_tracks.py
    rag_retrieve.py
    llm_correct.py
    evaluate_cer.py
    evaluate_speaker.py
    evaluate_terms.py
    evaluate_summary.py
    run_experiment.py

  results/
    transcripts_raw/
    transcripts_speaker/
    transcripts_corrected/
    summaries/
    tables/
    figures/

  demo/
    app.py

  docs/
    video_script.md
    contribution.md
    experiment_notes.md
```

---

# 3. Resource Migration

Copy resources from:

```text
D:\mlproject\project1_xutong
```

to the new repository.

## 3.1 Copy Mixed Audio

Source:

```text
D:\mlproject\project1_xutong\audio_exemple\ch\chongdie\mixed_test_audio
```

Target:

```text
resources/mixed_audio/
```

Expected files:

```text
NoOverlap.wav
LightOverlap.wav
MidOverlap.wav
HeavyOverlap.wav
OppositeOverlap.wav
```

## 3.2 Copy Separated Audio

Source:

```text
D:\mlproject\project1_xutong\audio_exemple\ch\chongdie\separated_audio
```

Target:

```text
resources/separated_audio/
```

Expected pattern:

```text
NoOverlap_spk1.wav
NoOverlap_spk2.wav
LightOverlap_spk1.wav
LightOverlap_spk2.wav
MidOverlap_spk1.wav
MidOverlap_spk2.wav
HeavyOverlap_spk1.wav
HeavyOverlap_spk2.wav
OppositeOverlap_spk1.wav
OppositeOverlap_spk2.wav
```

If filenames differ, create a mapping in:

```text
configs/config.yaml
```

## 3.3 Copy Snippets

Source:

```text
D:\mlproject\project1_xutong\audio_exemple\ch\chongdie\pianduan
```

Target:

```text
resources/snippets/
```

These files include:

```text
con_001.wav ... con_011.wav
pro_001.wav ... pro_015.wav
```

They can be used later for speaker profile, debate stance profile, or extra synthetic overlap data.

---

# 4. .gitignore

Write this `.gitignore`:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
env/
*.egg-info/

# IDE
.vscode/
.idea/

# Model cache
models/
checkpoints/
.cache/
huggingface/
torch_cache/

# Runtime outputs
results/transcripts_raw/*
results/transcripts_speaker/*
results/transcripts_corrected/*
results/summaries/*
results/tables/*
results/figures/*

# Keep result folders
!results/transcripts_raw/.gitkeep
!results/transcripts_speaker/.gitkeep
!results/transcripts_corrected/.gitkeep
!results/summaries/.gitkeep
!results/tables/.gitkeep
!results/figures/.gitkeep

# Large temporary files
*.tmp
*.log

# Environment secrets
.env
api_keys.json
```

Add `.gitkeep` files in empty result directories.

Do not commit model weights or API keys.

---

# 5. Project Core Idea

The project must not be a simple meeting transcription app.

The core research question is:

```text
Under different overlap intensities, when is speech separation useful,
when does it hurt, and can speaker-aware LLM correction plus glossary-RAG
improve the final transcript and summary?
```

Main method:

```text
Adaptive Overlap Routing + Speaker-Aware LLM Correction + Glossary-RAG
```

The system should compare five pipelines:

```text
P1: Mixed audio → ASR
P2: Mixed audio → alternative ASR
P3: Separated spk1/spk2 → ASR → speaker-attributed transcript
P4: P3 → speaker-aware LLM correction
P5: P4 → glossary-RAG enhanced correction
```

---

# 6. Experimental Dataset

Use the five existing Chinese overlap audio files as the main benchmark:

```text
NoOverlap.wav
LightOverlap.wav
MidOverlap.wav
HeavyOverlap.wav
OppositeOverlap.wav
```

Treat them as five overlap levels:

```text
NoOverlap        clean baseline
LightOverlap     light interruption
MidOverlap       medium overlap
HeavyOverlap     serious cross-talk
OppositeOverlap  debate-style conflicting overlap
```

These files are the core experiment set.

Do not start with large external datasets.

---

# 7. Manual Reference Transcripts

Before serious evaluation, create:

```text
references/reference_transcripts.json
```

Format:

```json
{
  "NoOverlap": {
    "audio": "NoOverlap.wav",
    "segments": [
      {
        "start": 0.0,
        "end": 3.2,
        "speaker": "SPEAKER_1",
        "text": "人工校对文本"
      }
    ]
  },
  "LightOverlap": {
    "audio": "LightOverlap.wav",
    "segments": []
  }
}
```

For the first MVP, if exact timestamps are difficult, allow simplified format:

```json
{
  "NoOverlap": {
    "speaker_1_text": "...",
    "speaker_2_text": "...",
    "full_text": "..."
  }
}
```

Manual reference transcripts are required for CER and speaker attribution evaluation.

---

# 8. Config File

Create:

```text
configs/config.yaml
```

Initial content:

```yaml
project:
  name: overlap-aware-speaker-asr
  language: zh

paths:
  mixed_audio_dir: resources/mixed_audio
  separated_audio_dir: resources/separated_audio
  snippets_dir: resources/snippets
  glossary_dir: resources/glossary
  reference_transcripts: references/reference_transcripts.json
  results_dir: results

audio_cases:
  - id: NoOverlap
    mixed: NoOverlap.wav
    separated:
      spk1: NoOverlap_spk1.wav
      spk2: NoOverlap_spk2.wav
    overlap_level: 0

  - id: LightOverlap
    mixed: LightOverlap.wav
    separated:
      spk1: LightOverlap_spk1.wav
      spk2: LightOverlap_spk2.wav
    overlap_level: 1

  - id: MidOverlap
    mixed: MidOverlap.wav
    separated:
      spk1: MidOverlap_spk1.wav
      spk2: MidOverlap_spk2.wav
    overlap_level: 2

  - id: HeavyOverlap
    mixed: HeavyOverlap.wav
    separated:
      spk1: HeavyOverlap_spk1.wav
      spk2: HeavyOverlap_spk2.wav
    overlap_level: 3

  - id: OppositeOverlap
    mixed: OppositeOverlap.wav
    separated:
      spk1: OppositeOverlap_spk1.wav
      spk2: OppositeOverlap_spk2.wav
    overlap_level: 4

asr:
  whisper_model: small
  language: zh
  device: auto

llm:
  provider: openai_compatible
  temperature: 0.1
  use_rag: true

evaluation:
  use_cer: true
  use_speaker_accuracy: true
  use_term_error_rate: true
  use_rouge_l: true
```

---

# 9. Module Implementation Plan

## 9.1 `src/config.py`

Purpose:

```text
Load config.yaml and provide project paths.
```

Required functions:

```python
load_config(path: str = "configs/config.yaml") -> dict
get_audio_cases(config: dict) -> list[dict]
resolve_path(*parts) -> str
```

Acceptance criteria:

```text
python -m src.config
```

should print loaded audio cases.

---

## 9.2 `src/audio_manifest.py`

Purpose:

```text
Generate a CSV manifest of all audio files.
```

Output:

```text
results/tables/audio_manifest.csv
```

Columns:

```text
case_id
audio_type
path
duration_sec
sample_rate
channels
overlap_level
```

Use Python libraries:

```text
wave
librosa
soundfile
pandas
```

Acceptance criteria:

```bash
python -m src.audio_manifest
```

should create `audio_manifest.csv`.

---

## 9.3 `src/transcribe_whisper.py`

Purpose:

```text
Transcribe mixed audio and separated audio using Whisper.
```

Use model priority:

```text
openai-whisper small or base for MVP
large-v3 only if GPU is available
```

Required outputs:

```text
results/transcripts_raw/{case_id}_mixed_whisper.json
results/transcripts_raw/{case_id}_spk1_whisper.json
results/transcripts_raw/{case_id}_spk2_whisper.json
```

JSON format:

```json
{
  "case_id": "HeavyOverlap",
  "audio_path": "resources/mixed_audio/HeavyOverlap.wav",
  "model": "whisper-small",
  "text": "...",
  "segments": [
    {
      "start": 0.0,
      "end": 2.1,
      "text": "..."
    }
  ],
  "runtime_sec": 12.5
}
```

Acceptance criteria:

```bash
python -m src.transcribe_whisper --case NoOverlap --mode mixed
python -m src.transcribe_whisper --case NoOverlap --mode separated
```

---

## 9.4 `src/transcribe_funasr.py`

Purpose:

```text
Optional Chinese ASR baseline using FunASR Paraformer.
```

This module is optional in the first MVP.

If FunASR environment is difficult, create a placeholder interface and document it in REPORT.md.

Required outputs:

```text
results/transcripts_raw/{case_id}_mixed_funasr.json
```

Acceptance criteria:

```bash
python -m src.transcribe_funasr --case NoOverlap --mode mixed
```

If not implemented, it should fail gracefully with:

```text
FunASR is not installed. Please install dependencies or skip this module.
```

---

## 9.5 `src/merge_speaker_tracks.py`

Purpose:

```text
Merge separated spk1/spk2 ASR outputs into speaker-attributed transcript.
```

Input:

```text
{case_id}_spk1_whisper.json
{case_id}_spk2_whisper.json
```

Output:

```text
results/transcripts_speaker/{case_id}_separated_speaker_transcript.json
```

Format:

```json
{
  "case_id": "HeavyOverlap",
  "method": "separated_tracks",
  "segments": [
    {
      "speaker": "SPEAKER_1",
      "start": 0.0,
      "end": 2.1,
      "text": "..."
    },
    {
      "speaker": "SPEAKER_2",
      "start": 1.8,
      "end": 3.4,
      "text": "..."
    }
  ],
  "full_text": "[SPEAKER_1] ...\n[SPEAKER_2] ..."
}
```

Sort segments by start time.

Acceptance criteria:

```bash
python -m src.merge_speaker_tracks --case HeavyOverlap
```

---

## 9.6 `src/compare_mixed_vs_separated.py`

Purpose:

```text
Compare direct mixed transcription with separated speaker-track transcription.
```

Input:

```text
results/transcripts_raw/{case_id}_mixed_whisper.json
results/transcripts_speaker/{case_id}_separated_speaker_transcript.json
```

Output:

```text
results/tables/mixed_vs_separated_comparison.csv
```

Columns:

```text
case_id
overlap_level
mixed_text
separated_text
mixed_runtime_sec
separated_runtime_sec
notes
```

Acceptance criteria:

```bash
python -m src.compare_mixed_vs_separated
```

---

# 10. RAG Module

## 10.1 `resources/glossary/terms.json`

Create a lightweight glossary.

Example:

```json
[
  {
    "term": "正方",
    "aliases": ["pro", "affirmative side", "支持方"],
    "description": "辩论中支持命题的一方"
  },
  {
    "term": "反方",
    "aliases": ["con", "negative side", "反对方"],
    "description": "辩论中反对命题的一方"
  },
  {
    "term": "交叉发言",
    "aliases": ["overlap", "cross-talk", "抢话"],
    "description": "两名或多名说话人同时发言的现象"
  },
  {
    "term": "说话人归属",
    "aliases": ["speaker attribution", "speaker assignment"],
    "description": "判断一句话属于哪位说话人的任务"
  }
]
```

## 10.2 `resources/glossary/speaker_profiles.json`

Example:

```json
{
  "SPEAKER_1": {
    "possible_role": "正方",
    "style": "表达较主动，可能提出支持命题的观点"
  },
  "SPEAKER_2": {
    "possible_role": "反方",
    "style": "表达较反驳，可能提出反对命题的观点"
  }
}
```

## 10.3 `src/rag_retrieve.py`

Purpose:

```text
Retrieve relevant glossary terms for a transcript.
```

MVP retrieval method:

```text
simple keyword match + fuzzy match
```

Do not use heavy vector database in MVP.

Required function:

```python
retrieve_terms(text: str, top_k: int = 5) -> list[dict]
```

Optional advanced version:

```text
FAISS / ChromaDB embedding retrieval
```

Acceptance criteria:

```bash
python -m src.rag_retrieve --case HeavyOverlap
```

should print relevant glossary terms.

---

# 11. LLM Correction Module

## 11.1 `src/llm_correct.py`

Purpose:

```text
Perform speaker-aware ASR correction and optional RAG-enhanced correction.
```

Input:

```text
results/transcripts_speaker/{case_id}_separated_speaker_transcript.json
resources/glossary/terms.json
```

Output:

```text
results/transcripts_corrected/{case_id}_corrected_no_rag.json
results/transcripts_corrected/{case_id}_corrected_with_rag.json
```

LLM prompt must be strict:

```text
You are an ASR post-processing assistant.

Task:
1. Correct only obvious ASR transcription errors.
2. Preserve the original meaning.
3. Do not add any information not present in the transcript.
4. Preserve all speaker labels.
5. If glossary terms are provided, prefer the official term spelling.
6. If uncertain, keep the original text unchanged.
7. Output valid JSON only.

Input speaker-attributed transcript:
...

Relevant glossary:
...
```

JSON output format:

```json
{
  "case_id": "HeavyOverlap",
  "corrected_segments": [
    {
      "speaker": "SPEAKER_1",
      "original_text": "...",
      "corrected_text": "...",
      "modification_reason": "fixed obvious ASR error"
    }
  ],
  "corrected_full_text": "...",
  "summary": {
    "topic": "...",
    "speaker_positions": {
      "SPEAKER_1": "...",
      "SPEAKER_2": "..."
    },
    "key_points": [],
    "overlap_observation": "..."
  }
}
```

Important:

```text
Temperature must be low, ideally 0.1.
Do not allow creative rewriting.
Do not remove speaker labels.
Do not invent new claims.
```

Acceptance criteria:

```bash
python -m src.llm_correct --case HeavyOverlap --rag false
python -m src.llm_correct --case HeavyOverlap --rag true
```

---

# 12. Evaluation Modules

## 12.1 `src/evaluate_cer.py`

Purpose:

```text
Compute Chinese Character Error Rate.
```

Formula:

```text
CER = (Substitution + Deletion + Insertion) / Number of reference characters
```

Implement using:

```text
python-Levenshtein
or custom dynamic programming edit distance
```

Inputs:

```text
references/reference_transcripts.json
results/transcripts_raw/*.json
results/transcripts_corrected/*.json
```

Output:

```text
results/tables/cer_results.csv
```

Columns:

```text
case_id
overlap_level
method
cer
edit_distance
reference_length
```

Methods:

```text
mixed_whisper
separated_whisper
corrected_no_rag
corrected_with_rag
```

Acceptance criteria:

```bash
python -m src.evaluate_cer
```

---

## 12.2 `src/evaluate_speaker.py`

Purpose:

```text
Evaluate speaker attribution accuracy.
```

MVP metric:

```text
Speaker Attribution Accuracy = correctly assigned speaker segments / total reference segments
```

If exact timestamps are unavailable, use simplified manual segment matching.

Output:

```text
results/tables/speaker_attribution_results.csv
```

Columns:

```text
case_id
method
num_reference_segments
num_correct_speaker_segments
speaker_accuracy
notes
```

Acceptance criteria:

```bash
python -m src.evaluate_speaker
```

---

## 12.3 `src/evaluate_terms.py`

Purpose:

```text
Evaluate terminology error rate and hotword recall.
```

Glossary terms:

```text
resources/glossary/terms.json
```

Metrics:

```text
Term Error Rate = wrong glossary terms / total expected glossary terms
Hotword Recall = correctly recovered glossary terms / expected glossary terms
```

Output:

```text
results/tables/term_error_results.csv
```

Columns:

```text
case_id
method
expected_terms
recognized_terms
missing_terms
wrong_terms
term_error_rate
hotword_recall
```

Acceptance criteria:

```bash
python -m src.evaluate_terms
```

---

## 12.4 `src/evaluate_summary.py`

Purpose:

```text
Evaluate summary quality.
```

MVP metrics:

```text
ROUGE-L
manual human rating placeholder
```

If ROUGE is difficult, implement simple longest common subsequence ratio.

Input:

```text
references/reference_summaries.json
results/transcripts_corrected/*.json
```

Output:

```text
results/tables/summary_results.csv
```

Acceptance criteria:

```bash
python -m src.evaluate_summary
```

---

# 13. Main Experiment Runner

## `src/run_experiment.py`

Purpose:

```text
Run the complete experiment pipeline.
```

Command:

```bash
python -m src.run_experiment --all
```

Pipeline:

```text
1. Load config
2. Generate audio manifest
3. Transcribe mixed audio
4. Transcribe separated spk1/spk2 audio
5. Merge separated tracks into speaker-attributed transcript
6. Compare mixed vs separated
7. Run LLM correction without RAG
8. Run LLM correction with RAG
9. Evaluate CER
10. Evaluate speaker attribution
11. Evaluate term error
12. Evaluate summary
13. Save final tables
```

Must support partial execution:

```bash
python -m src.run_experiment --stage asr
python -m src.run_experiment --stage merge
python -m src.run_experiment --stage llm
python -m src.run_experiment --stage eval
```

---

# 14. Demo App

## `demo/app.py`

Use Streamlit.

MVP UI:

```text
1. Select audio case
2. Play mixed audio
3. Show mixed ASR transcript
4. Show separated speaker transcript
5. Show LLM corrected transcript
6. Show RAG-enhanced corrected transcript
7. Show metrics table
```

Do not build complex frontend.

Command:

```bash
streamlit run demo/app.py
```

---

# 15. README.md Content

README should include:

```text
1. Project title
2. Problem statement
3. Difference from XuTong baseline
4. Method overview
5. Repository structure
6. Installation
7. How to run
8. Experiment design
9. Results
10. Team contribution
```

Key statement:

```text
This project extends XuTong’s multi-speaker conversation management system by focusing on overlap-aware speaker-attributed ASR. Instead of applying speech separation to all audio, we evaluate different overlap intensities and test whether separated speaker tracks, speaker-aware LLM correction, and glossary-based RAG improve transcription, attribution, and summary quality.
```

---

# 16. REPORT.md Structure

Use paper-style structure:

```text
1. Introduction
2. Related Work
   2.1 ASR for multi-speaker conversations
   2.2 Speaker diarization
   2.3 Speech separation for overlap
   2.4 LLM correction and RAG
3. Method
   3.1 Mixed audio ASR baseline
   3.2 Separated speaker-track ASR
   3.3 Adaptive overlap routing
   3.4 Speaker-aware LLM correction
   3.5 Glossary-RAG correction
4. Experiments
   4.1 Dataset
   4.2 Pipelines
   4.3 Metrics
5. Results
   5.1 CER comparison
   5.2 Speaker attribution comparison
   5.3 Term error comparison
   5.4 Summary comparison
6. Discussion
   6.1 When separation helps
   6.2 When separation may hurt
   6.3 Limitations
7. Conclusion
```

---

# 17. Implementation Priority

## Stage 1: GitHub and Structure

Goal:

```text
Create repository, folders, config, README skeleton.
```

Deliverables:

```text
GitHub repo
project structure
initial commit
```

## Stage 2: Resource Migration

Goal:

```text
Copy audio resources into project.
Create config mapping.
Create audio manifest.
```

Deliverables:

```text
resources/
configs/config.yaml
results/tables/audio_manifest.csv
```

## Stage 3: ASR Baseline

Goal:

```text
Run Whisper on mixed and separated audio.
```

Deliverables:

```text
results/transcripts_raw/*.json
```

## Stage 4: Speaker Transcript

Goal:

```text
Merge spk1/spk2 separated transcripts.
```

Deliverables:

```text
results/transcripts_speaker/*.json
```

## Stage 5: Manual Reference

Goal:

```text
Create reference transcripts.
```

Deliverables:

```text
references/reference_transcripts.json
```

## Stage 6: Evaluation

Goal:

```text
Compute CER and initial comparison.
```

Deliverables:

```text
results/tables/cer_results.csv
```

## Stage 7: LLM Correction

Goal:

```text
Run speaker-aware LLM correction without RAG.
```

Deliverables:

```text
results/transcripts_corrected/*_corrected_no_rag.json
```

## Stage 8: RAG Enhancement

Goal:

```text
Add glossary retrieval and RAG-enhanced correction.
```

Deliverables:

```text
resources/glossary/terms.json
results/transcripts_corrected/*_corrected_with_rag.json
```

## Stage 9: Final Metrics and Figures

Goal:

```text
Generate tables and plots.
```

Deliverables:

```text
results/tables/*.csv
results/figures/*.png
```

## Stage 10: Demo and Report

Goal:

```text
Create Streamlit demo and final documentation.
```

Deliverables:

```text
demo/app.py
README.md
REPORT.md
docs/video_script.md
docs/contribution.md
```

---

# 18. Required Experiment Table

Final results should include this comparison table:

```text
case_id | overlap_level | method | CER | speaker_accuracy | term_error_rate | hotword_recall | runtime_sec
```

Methods:

```text
mixed_whisper
separated_whisper
corrected_no_rag
corrected_with_rag
```

Expected final visualization:

```text
Figure 1: CER vs overlap level
Figure 2: Term Error Rate before and after RAG
Figure 3: Runtime comparison
Figure 4: Speaker attribution accuracy
```

---

# 19. Risk Control

## Risk 1: Heavy models cannot run

Solution:

```text
Use Whisper base/small first.
Use existing separated audio instead of running SepFormer.
Keep FunASR and SepFormer optional.
```

## Risk 2: LLM hallucinates

Solution:

```text
Use strict JSON output.
Use temperature 0.1.
Tell model not to add information.
Keep original and corrected text side by side.
```

## Risk 3: No reference transcript

Solution:

```text
Manually annotate the five short audio files.
This is mandatory for real evaluation.
```

## Risk 4: Speaker timestamps are imperfect

Solution:

```text
First evaluate speaker-level full text.
Only add timestamp-level evaluation later if time allows.
```

## Risk 5: Project becomes too large

Solution:

```text
Do not train models.
Do not modify Whisper architecture.
Do not implement RoPE.
Do not build complex frontend.
Do not benchmark too many ASR models.
```

---

# 20. What Not To Do

Do not implement these in MVP:

```text
Training ASR model
Training diarization model
Changing Whisper/RoPE architecture
Full XuTong system replication
Age/gender/emotion prediction
Mobile deployment
Large-scale external dataset evaluation
Complex vector database RAG
```

Optional extensions only after MVP:

```text
FunASR comparison
WhisperX forced alignment
pyannote diarization
SepFormer or MossFormer2 automatic separation
cpWER / WDER advanced metrics
```

---

# 21. First Concrete Tasks for Codex

Start now with these tasks in order:

```text
Task 1:
Create project repository structure.

Task 2:
Write .gitignore, README skeleton, REPORT skeleton.

Task 3:
Create configs/config.yaml.

Task 4:
Copy audio files from D:\mlproject\project1_xutong into resources/.

Task 5:
Implement src/config.py.

Task 6:
Implement src/audio_manifest.py.

Task 7:
Run audio manifest generation and save results/tables/audio_manifest.csv.

Task 8:
Commit changes with message:
"create project skeleton and audio manifest"
```

After Task 8, stop and report:

```text
1. Files created
2. Files copied
3. Audio manifest summary
4. Any missing paths or filename mismatches
5. Next recommended step
```

---

# 22. Initial Commit Plan

Use meaningful commits:

```bash
git add .
git commit -m "create project skeleton"
git add resources configs src
git commit -m "add audio resources and config mapping"
git add src/audio_manifest.py results/tables/audio_manifest.csv
git commit -m "implement audio manifest generation"
```

Each team member should later work on a separate branch:

```text
feature/asr-baseline
feature/speaker-merge
feature/rag-correction
feature/evaluation
feature/demo
feature/report
```

---

# 23. Final Success Criteria

The project is successful if it can show:

```text
1. ASR performance changes as overlap intensity increases.
2. Separated speaker-track transcription improves heavy overlap cases.
3. Separation may not be necessary for clean/no-overlap cases.
4. Speaker-aware LLM correction improves readability and attribution.
5. Glossary-RAG reduces terminology and role-label errors.
6. The system produces structured speaker-attributed summaries.
7. Experiments are reproducible from GitHub.
```

Final deliverables:

```text
GitHub repository
README.md
REPORT.md
Source code
Experiment tables
Figures
Streamlit demo
English presentation video
Contribution document
```
