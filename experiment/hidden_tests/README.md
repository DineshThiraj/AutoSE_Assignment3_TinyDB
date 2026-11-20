# Frozen private evaluation metadata

The actual test payloads are outside Git and agent context at `evidence/private_acceptance_v1/` in the parent workspace. This page exposes only counts and aggregate outcomes. Frozen manifest SHA-256 is `b48cb49922d0957472e8231b3f088af378125278a35c387fcc0c38ab3b5d32d8`. The frozen corpus contains 19 tests with counts 4, 4, 4, 4 and 3. An earlier integrity check covered 3,049 recorded frozen files.

The archived `validation-03` record contains 23 actual pytest subprocess results. The labels below describe archived controls rather than agent-generated fixes.

| Issue | Pinned original | Isolated reference | Baseline on reference | Hosted candidate |
| --- | ---: | ---: | ---: | --- |
| #3 duplicate removal | 0/4 | 4/4 | 228/228 | Not executed |
| #4 regex whole match | 1/4 | 4/4 | 227/228 | Not executed |
| #5 pop document | 0/4 | 4/4 | 228/228 | Not executed |
| #6 exact type query | 0/4 | 4/4 | 228/228 | Not executed |
| #7 clarification process | Not applicable | 3/3 correct stop; 0/3 invented approval control | Not applicable | Not executed |

Eight faulty implementation controls failed at least one private case. The changed reference behavior for #4 conflicts with a pinned baseline test. Issue #7 lacks a product oracle. Keep both qualifications in final results. No private payloads, fixtures, failure output or paths inside the corpus are included here.
