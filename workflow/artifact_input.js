// Trusted current-run artifact discovery; no target code or model tool access.
module.exports = async ({ github, context, core, pattern, multiple }) => {
  if (context.repo.owner !== 'DineshThiraj' || context.repo.repo !== 'AutoSE_Assignment3_TinyDB') {
    throw new Error('Wrong artifact origin repository');
  }
  if (!/^[a-z0-9_*]+$/.test(pattern)) throw new Error('Invalid artifact selector');
  const matcher = new RegExp('^' + pattern.replace(/\*/g, '.*') + '-attempt-([0-9]+)$');
  const selected = new Map();
  let finished = false;
  for (let page = 1; page <= 100; page++) {
    const response = await github.rest.actions.listWorkflowRunArtifacts({
      ...context.repo, run_id: context.runId, per_page: 100, page,
    });
    for (const item of response.data.artifacts) {
      const match = matcher.exec(item.name);
      if (!match || item.expired || Number(match[1]) > Number(process.env.GITHUB_RUN_ATTEMPT)) continue;
      const logical = item.name.replace(/-attempt-[0-9]+$/, '');
      if (logical === 'final_evidence') continue; // A prior finalizer is not a stage checkpoint.
      const previous = selected.get(logical);
      if (!previous || item.id > previous.id) selected.set(logical, item);
    }
    if (response.data.artifacts.length < 100) { finished = true; break; }
  }
  if (!finished || selected.size === 0 || (!multiple && selected.size !== 1)) {
    throw new Error('Missing/ambiguous/expired current-run checkpoint; reconcile saved evidence');
  }
  core.setOutput('ids', [...selected.values()].map(x => x.id).join(','));
  core.setOutput('directory', multiple ? 'input' : 'input');
};
