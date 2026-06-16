# AudioDepth Router Exploratory Study

## Status

Label: Frontier Branch Only / Exploratory Research

This work currently lives on `frontier/audio-depth-router` and is not part of
the stable mainline claim. It needs separate review before any merge.

## Why It Exists

AudioDepth routing explores whether audio-depth style signals can help decide
when overlap-aware ASR should use mixed audio, separated speaker tracks, or a
more cautious fallback. The idea is research-motivated, but the current branch
should be treated as exploratory until its code, data, and claims are separated
and reviewed.

## What Can Be Merged Later

| Component | Merge Strategy | Notes |
|---|---|---|
| Core code | Review and extract minimal modules | No large artifacts |
| Documentation | Convert into curated `docs/frontier/` entry | Must separate claim from observation |
| Lightweight examples | Keep tiny samples only | No heavy `.npy`, `.png`, or model-weight payloads |
| Large artifacts | Keep outside repo or attach to release/artifact storage | Do not merge directly into `main` |

## What Must Not Be Merged Directly

- model weights
- large `.npy` files
- bulk generated `.png` depth maps
- raw exploratory result dumps
- duplicated wave/writeback records
- unverified benchmark claims

## Required Before Mainline Merge

1. Separate code from artifacts.
2. Add minimal tests.
3. Add a small reproducible example.
4. Document dependencies.
5. Add result claim boundaries.
6. Confirm storage strategy for large artifacts.
7. Open a PR with a focused diff.

## Relation to Contributions

If this work is part of a member's contribution, link to
[CONTRIBUTIONS.md](../../CONTRIBUTIONS.md), but do not replace contribution
records with technical research notes.
