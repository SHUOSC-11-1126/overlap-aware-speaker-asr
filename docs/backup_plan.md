# Backup Plan

This project has already reached the core technical milestone, so the backup plan is about preserving the working state rather than changing it.

## 1. Git Tag Backup

Recommended tag:

```text
wufangzhou-core-complete
```

Suggested commands:

```powershell
git tag -a wufangzhou-core-complete -m "Core technical pipeline completed by WUFANGZHOU"
git push origin wufangzhou-core-complete
```

## 2. Handoff Branch

Recommended branch:

```text
handoff/wufangzhou-core-complete
```

Suggested commands:

```powershell
git checkout -b handoff/wufangzhou-core-complete
git push origin handoff/wufangzhou-core-complete
git checkout main
```

## 3. Local Zip Backup

Recommended output:

```text
backups/overlap-aware-speaker-asr_wufangzhou_core_complete.zip
```

Use the local backup script to create a commit-stamped zip snapshot.

## 4. Optional Mirror Repository

Only create a second backup repository if the team needs stronger protection or if repository access may change. Do not use a mirror as the main working repository unless explicitly agreed.
