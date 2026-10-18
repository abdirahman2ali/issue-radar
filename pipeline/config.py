from typesafe_sdk import Choice, Noul, Score

REPOS = ["anthropics/claude-code"]
MODEL = "jev-latest"
# The board shows only complete UTC days, and the first and last day of a rolling window are
# partial. 8 days kept means 7 complete days shown.
WINDOW_DAYS = 8
BACKFILL_DAYS = WINDOW_DAYS  # a fresh state should cover the whole window, not part of it
MAX_ISSUES = 2500
# Deleted or transferred issues are removed from the data. If a run would remove more than this
# many at once, assume the fetch came back incomplete and remove nothing.
MAX_PRUNE = 25
BODY_CHARS = 2000
EXCERPT_CHARS = 300
CONCURRENCY = 8

QUESTIONS = {
    "category": Choice(
        instructions="What kind of GitHub issue is this?",
        criteria={
            "bug": "Something is broken or behaves incorrectly",
            "feature_request": "Asks for new behavior or an improvement",
            "question": "Asks how to do something or for help",
            "docs": "About documentation being missing or wrong",
            "other": "Anything else",
        },
    ),
    "area": Choice(
        instructions="Which part of the product does this issue mainly concern?",
        criteria={
            "cli_terminal": (
                "The command line tool in a terminal: rendering, input, keyboard shortcuts, "
                "scrolling, slash commands, terminal UI"
            ),
            "ide_integration": "VS Code, JetBrains, or other editor extensions and integrations",
            "desktop_app": (
                "The Claude desktop app and its Code tab: windows, sessions, rendering, "
                "crashes or UI problems in the app rather than the terminal"
            ),
            "web_cloud": (
                "Claude Code on the web, cloud or remote sessions, routines, cowork, "
                "scheduled or background agents"
            ),
            "mcp_tools": "MCP servers, tool calls, hooks, plugins, skills, subagents",
            "model_behavior": (
                "Quality of the model's output or reasoning: wrong or made up answers, "
                "ignoring instructions, refusals, bad edits, losing context"
            ),
            "permissions_security": "Permissions, sandboxing, approvals, security",
            "performance": "Slowness, high memory or CPU use, hangs, token or context usage",
            "auth_billing": "Login, authentication, accounts, plans, rate limits, billing",
            "install_update": (
                "Installing or updating the product, packaging, environment setup, "
                "platform specific breakage on Windows, WSL, Linux or macOS"
            ),
            "other": "None of the above",
        },
    ),
    "severity": Score(
        instructions="How severe is the problem for the user who reported it?",
        criteria=[
            "Minor annoyance or cosmetic, easy workaround",
            "Noticeable problem, workaround exists",
            "Major problem that blocks an important workflow",
            "Blocking or data loss, product unusable",
        ],
    ),
    "is_urgent": Noul(instructions="The issue conveys urgency or time sensitivity"),
    "is_regression": Noul(
        instructions="The issue says something that used to work stopped working after an update"
    ),
    "has_repro": Noul(instructions="The issue includes clear steps to reproduce the problem"),
    "needs_info": Noul(
        instructions="Maintainers would need to ask the reporter for more information"
    ),
}
