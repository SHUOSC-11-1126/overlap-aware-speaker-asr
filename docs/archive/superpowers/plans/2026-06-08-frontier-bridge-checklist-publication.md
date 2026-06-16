# Frontier Bridge Checklist Publication Plan

## Goal

Publish the generated bridge checklist artifacts that are already produced by existing frontier modules and already referenced by the project docs.

## Why This Next

After publishing the `project_harness` coordination artifacts, a small set of generated checklist files still remains ignored:

- `meeteval_dry_run_bridge_checklist`
- `speaker_profile_checklist`
- `speaker_profile_method_bridge_checklist`

The source modules and tests already define these outputs. The docs already point at the MeetEval and speaker-profile bridge checklists. Publishing the files makes those references resolvable without changing the experimental scope.

## Scope

- whitelist the current MeetEval dry-run bridge checklist outputs
- whitelist the current speaker-profile checklist outputs
- regenerate outputs from the existing modules
- commit generated CSV / JSON / Markdown artifacts only
- keep all claims framed as coordination or checklist artifacts

## Verification

- run `python3 -m src.export_meeteval_compatibility`
- run `python3 -m src.speaker_profile_similarity`
- run `python3 -m unittest tests.test_export_meeteval_compatibility tests.test_speaker_profile_similarity -v`
