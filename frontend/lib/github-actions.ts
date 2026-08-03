type GithubDispatchConfig = {
  token: string;
  owner: string;
  repo: string;
  workflowId: string;
  ref: string;
};

function getGithubDispatchConfig(): GithubDispatchConfig {
  const token = process.env.GITHUB_ACTIONS_TOKEN;
  const owner = process.env.GITHUB_REPO_OWNER;
  const repo = process.env.GITHUB_REPO_NAME;
  const workflowId = process.env.GITHUB_WORKFLOW_ID || "tier-a-predictions.yml";
  const ref = process.env.GITHUB_WORKFLOW_REF || "main";

  if (!token || !owner || !repo) {
    throw new Error(
      "Missing GitHub dispatch config. Set GITHUB_ACTIONS_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME."
    );
  }

  return { token, owner, repo, workflowId, ref };
}

export async function triggerPredictionWorkflow(): Promise<{ actionsUrl: string }> {
  const { token, owner, repo, workflowId, ref } = getGithubDispatchConfig();

  const endpoint = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(
    workflowId
  )}/dispatches`;

  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref }),
    cache: "no-store",
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Failed to dispatch workflow (${res.status}): ${errBody}`);
  }

  return {
    actionsUrl: `https://github.com/${owner}/${repo}/actions/workflows/${workflowId}`,
  };
}
