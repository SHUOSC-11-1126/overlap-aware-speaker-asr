## Summary

- 

## Risk Level

LOW / MEDIUM / HIGH

## Critical Skeleton Change

- `none`, or list authority/skeleton files touched.

## GitNexus Impact

- Expected impact:
- Guard-sensitive docs:

## Verification

- [ ] `python -m scripts.check_environment`
- [ ] `python -m unittest discover -s tests -p 'test_*.py' -q`
- [ ] `python -m src.project_harness` if docs/results status changed
- [ ] Links and claim boundaries checked for docs-only changes

## Claim Boundary

- Gold/manual:
- Silver/synthetic:
- Frontier/diagnostic:
- Not claimed:

## Docs-only Example

```text
Risk Level: LOW
Critical Skeleton Change: README.md authority-docs only
GitNexus Impact: detect_changes should classify as docs-only; no benchmark skeleton or runtime contract changed.
Verification: python -m scripts.check_environment; markdown links checked; claim boundary unchanged.
```
