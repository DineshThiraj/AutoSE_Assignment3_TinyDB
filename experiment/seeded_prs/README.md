# Reviewer-check fixtures

Five independent, unapplied unified diffs against the original TinyDB source. These are **local fixtures**, with labels derived from source inspection and verified to apply cleanly. No PR was created for them. Reviewer execution, detections, misses, and false positives are **not measured**. Keep this directory away from any future blinded reviewer inputs. Scope the reviewer to the paired issue and candidate diff/source.

| Fixture | Ground-truth label | Behavior intended to probe |
| --- | --- | --- |
| [01 Cache copy](01-cache-copy.patch) | Defect · cache result aliasing | Mutating a caller-visible cached result list can modify the next caller's results. |
| [02 Flag identity](02-flag-identity.patch) | Defect · cache identity | Regex flag variants can share a query-cache identity. |
| [03 Middleware flush](03-middleware-flush.patch) | Defect · lifecycle | Closing write-behind storage can discard buffered data. |
| [04 Custom document](04-custom-document.patch) | Defect · extension contract | The altered conversion path bypasses the configured document class. |
| [05 Clean documentation](05-clean-doc.patch) | Clean control | Clarifies flush documentation without changing executable code. |

Check applicability without applying changes:

```sh
for patch in experiment/seeded_prs/*.patch; do git apply --check "$patch"; done
```

These are submission-time evaluation inputs. The public labels cannot be hidden retroactively from a reviewer already trained on or shown these files. A blind quantitative test would need different private seeds or a sandbox verified to withhold labels.
