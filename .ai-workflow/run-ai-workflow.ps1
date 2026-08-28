$ErrorActionPreference = "Stop"

$ExpectedRepo   = "C:\AI-Projects\OpenMANET-Pi5\firmware"
$ExpectedBranch = "pi5-wm6108-port"

$Current = (Get-Location).Path

if ($Current.TrimEnd("\") -ne $ExpectedRepo.TrimEnd("\")) {
    throw "STOPPED: Run this workflow only from $ExpectedRepo. Current directory: $Current"
}

if (-not (Test-Path ".git")) {
    throw "STOPPED: This is not the expected Git repository."
}

if (-not (Test-Path "CLAUDE.md")) {
    throw "STOPPED: CLAUDE.md is missing."
}

if (-not (Test-Path ".ai-workflow\task.md")) {
    throw "STOPPED: .ai-workflow\task.md is missing."
}

$Branch = (git branch --show-current).Trim()

if ($Branch -ne $ExpectedBranch) {
    throw "STOPPED: Expected branch '$ExpectedBranch'; current branch is '$Branch'."
}

$ClaudeCommand = Get-Command claude -ErrorAction SilentlyContinue

if (-not $ClaudeCommand) {
    throw "STOPPED: Claude Code command 'claude' was not found in PATH."
}

Write-Host ""
Write-Host "OpenMANET Pi 5 autonomous workflow starting..."
Write-Host "Repository : $ExpectedRepo"
Write-Host "Branch     : $Branch"
Write-Host ""

claude "Read CLAUDE.md and .ai-workflow/task.md completely before acting. Treat CLAUDE.md as the permanent project authority and task.md as the authoritative current task. Execute the task autonomously now. Use subagents/helpers aggressively as directed. Make safe routine engineering decisions yourself. Do not stop merely to report analysis when implementation, builds, debugging, or validation can continue. Minimize owner interaction and only interrupt for the owner-required cases defined in CLAUDE.md."
