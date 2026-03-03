import { tool } from "@opencode-ai/plugin"

async function runGlab(args: string[]) {
  const proc = Bun.spawn(["glab", ...args], {
    stdout: "pipe",
    stderr: "pipe",
  })

  const stdout = await new Response(proc.stdout).text()
  const stderr = await new Response(proc.stderr).text()
  const exitCode = await proc.exited

  if (exitCode !== 0) {
    throw new Error(
      `glab failed (exit ${exitCode})\n` +
        `command: glab ${args.join(" ")}\n` +
        `stderr: ${stderr || "(empty)"}`,
    )
  }

  return stdout.trim()
}

function repoToProjectPath(repo: string): string {
  let value = repo.trim()
  value = value.replace(/\.git$/, "")

  // git@host:group/project
  if (value.startsWith("git@") && value.includes(":")) {
    value = value.split(":", 2)[1] || value
  }

  // https://host/group/project
  value = value.replace(/^https?:\/\//, "")

  // host/group/project -> group/project
  const parts = value.split("/").filter(Boolean)
  if (parts.length >= 3 && parts[0].includes(".")) {
    value = parts.slice(1).join("/")
  } else {
    value = parts.join("/")
  }

  return value.replace(/^\//, "")
}

function toWikiSlug(title: string): string {
  return title
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
}

export const createissue = tool({
  description: "Create a GitLab issue using glab CLI",
  args: {
    repo: tool.schema
      .string()
      .describe(
        "GitLab repo in format host/group/project, e.g. codebase.helmholtz.cloud/santiago.casascastro/MetadataMappingSssOM",
      ),
    title: tool.schema.string().describe("Issue title"),
    description: tool.schema
      .string()
      .optional()
      .describe("Issue description body (Markdown supported)"),
    labels: tool.schema
      .array(tool.schema.string())
      .optional()
      .describe("Optional labels, e.g. ['planning', 'rag']"),
    assignees: tool.schema
      .array(tool.schema.string())
      .optional()
      .describe("Optional assignees, e.g. ['@me']"),
  },
  async execute(args) {
    const cmd = ["issue", "create", "-R", args.repo, "--title", args.title]

    if (args.description && args.description.trim()) {
      cmd.push("--description", args.description)
    }
    if (args.labels && args.labels.length > 0) {
      cmd.push("--label", args.labels.join(","))
    }
    if (args.assignees && args.assignees.length > 0) {
      cmd.push("--assignee", args.assignees.join(","))
    }

    const output = await runGlab(cmd)
    return output || "Issue created."
  },
})

export const readissues = tool({
  description: "Read GitLab issues for a repository",
  args: {
    repo: tool.schema
      .string()
      .describe(
        "GitLab repo in format host/group/project, e.g. codebase.helmholtz.cloud/santiago.casascastro/MetadataMappingSssOM",
      ),
    state: tool.schema
      .enum(["opened", "closed", "all"])
      .default("opened")
      .describe("Issue state filter"),
    limit: tool.schema
      .number()
      .int()
      .min(1)
      .max(100)
      .default(20)
      .describe("Maximum number of issues to list"),
    labels: tool.schema
      .array(tool.schema.string())
      .optional()
      .describe("Optional label filters"),
    search: tool.schema
      .string()
      .optional()
      .describe("Optional search query"),
  },
  async execute(args) {
    const cmd = ["issue", "list", "-R", args.repo, "-P", String(args.limit)]

    // glab does not support a --state flag for issue list.
    // opened: default behavior (no extra flag)
    // closed: -c
    // all: -A
    if (args.state === "closed") {
      cmd.push("-c")
    } else if (args.state === "all") {
      cmd.push("-A")
    }

    if (args.labels && args.labels.length > 0) {
      cmd.push("--label", args.labels.join(","))
    }
    if (args.search && args.search.trim()) {
      cmd.push("--search", args.search)
    }

    const output = await runGlab(cmd)
    return output || "No issues found."
  },
})

export const batchcreate = tool({
  description: "Create multiple GitLab issues in one call",
  args: {
    repo: tool.schema
      .string()
      .describe(
        "GitLab repo in format host/group/project, e.g. codebase.helmholtz.cloud/santiago.casascastro/MetadataMappingSssOM",
      ),
    issues: tool.schema
      .array(
        tool.schema.object({
          title: tool.schema.string(),
          description: tool.schema.string().optional(),
          labels: tool.schema.array(tool.schema.string()).optional(),
          assignees: tool.schema.array(tool.schema.string()).optional(),
        }),
      )
      .describe("List of issues to create"),
  },
  async execute(args) {
    const results: Array<{ title: string; ok: boolean; output: string }> = []

    for (const item of args.issues) {
      try {
        const cmd = ["issue", "create", "-R", args.repo, "--title", item.title]
        if (item.description && item.description.trim()) {
          cmd.push("--description", item.description)
        }
        if (item.labels && item.labels.length > 0) {
          cmd.push("--label", item.labels.join(","))
        }
        if (item.assignees && item.assignees.length > 0) {
          cmd.push("--assignee", item.assignees.join(","))
        }

        const output = await runGlab(cmd)
        results.push({ title: item.title, ok: true, output })
      } catch (err) {
        results.push({
          title: item.title,
          ok: false,
          output: err instanceof Error ? err.message : String(err),
        })
      }
    }

    return JSON.stringify(results, null, 2)
  },
})

export const createmr = tool({
  description: "Create a GitLab merge request using glab CLI",
  args: {
    repo: tool.schema
      .string()
      .describe(
        "GitLab repo in format host/group/project, e.g. codebase.helmholtz.cloud/santiago.casascastro/MetadataMappingSssOM",
      ),
    source_branch: tool.schema.string().describe("Source branch name"),
    target_branch: tool.schema
      .string()
      .default("main")
      .describe("Target branch name"),
    title: tool.schema.string().describe("Merge request title"),
    description: tool.schema
      .string()
      .optional()
      .describe("Merge request description"),
    draft: tool.schema
      .boolean()
      .default(false)
      .describe("Create as draft merge request"),
    remove_source_branch: tool.schema
      .boolean()
      .default(false)
      .describe("Request source branch removal after merge"),
  },
  async execute(args) {
    const cmd = [
      "mr",
      "create",
      "-R",
      args.repo,
      "--source-branch",
      args.source_branch,
      "--target-branch",
      args.target_branch,
      "--title",
      args.title,
    ]

    if (args.description && args.description.trim()) {
      cmd.push("--description", args.description)
    }
    if (args.draft) {
      cmd.push("--draft")
    }
    if (args.remove_source_branch) {
      cmd.push("--remove-source-branch")
    }

    const output = await runGlab(cmd)
    return output || "Merge request created."
  },
})

export const writewiki = tool({
  description: "Create or update a GitLab wiki page using glab API",
  args: {
    repo: tool.schema
      .string()
      .describe(
        "GitLab repo in format host/group/project, e.g. codebase.helmholtz.cloud/santiago.casascastro/MetadataMappingSssOM",
      ),
    title: tool.schema.string().describe("Wiki page title"),
    content: tool.schema.string().describe("Wiki page markdown content"),
    slug: tool.schema
      .string()
      .optional()
      .describe("Optional wiki slug; defaults to title-derived slug"),
  },
  async execute(args) {
    const projectPath = repoToProjectPath(args.repo)
    const project = encodeURIComponent(projectPath)
    const slug = args.slug?.trim() ? args.slug.trim() : toWikiSlug(args.title)
    const encodedSlug = encodeURIComponent(slug)

    const createCmd = [
      "api",
      "-X",
      "POST",
      `projects/${project}/wikis`,
      "-f",
      `title=${args.title}`,
      "--raw-field",
      `content=${args.content}`,
    ]

    try {
      const output = await runGlab(createCmd)
      return output || "Wiki page created."
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      const exists =
        message.includes("already been taken") ||
        message.includes("already exists") ||
        message.includes("has already been taken")
      if (!exists) {
        throw err
      }
    }

    const updateCmd = [
      "api",
      "-X",
      "PUT",
      `projects/${project}/wikis/${encodedSlug}`,
      "--raw-field",
      `content=${args.content}`,
    ]
    const updated = await runGlab(updateCmd)
    return updated || "Wiki page updated."
  },
})
