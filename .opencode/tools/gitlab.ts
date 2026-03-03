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
