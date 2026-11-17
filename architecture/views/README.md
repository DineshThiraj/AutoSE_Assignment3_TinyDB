# Architecture views status

component.dot is the reviewed initial component view, reproducibly rendered with Graphviz to component.svg and component.png. It is not an implemented architecture claim. Student choices and deferred model setup are recorded in ../STUDENT_REVIEW.md in the publication tree. Rebuild: dot -Tsvg component.dot -o component.svg and dot -Tpng component.dot -o component.png.

stage-map.md is the reviewed initial six-stage contract table.

sequence-plan.txt is Mermaid planning notation; sequence-plan.dot/svg/png provide a rendered proposed sequence. The required real-run sequence view cannot be produced honestly until an actual hosted run exists; derive it from that run's issue, stage events, SHAs, PR and review URLs, then render and inspect it. Do not relabel the proposal as real execution.
