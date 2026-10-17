from typesafe_sdk import Choice, Noul, Score

REPOS = ["anthropics/claude-code"]
MODEL = "jev-latest"
WINDOW_DAYS = 7
BACKFILL_DAYS = 3
MAX_ISSUES = 2500
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
            "cli_terminal": "Command line interface, terminal rendering, input, shortcuts",
            "ide_integration": "VS Code, JetBrains, or other editor integrations",
            "mcp_tools": "MCP servers, tool calls, hooks, plugins, skills, subagents",
            "permissions_security": "Permissions, sandboxing, approvals, security",
            "performance": "Slowness, high memory or CPU use, hangs, token or context usage",
            "auth_billing": "Login, authentication, accounts, plans, rate limits, billing",
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
