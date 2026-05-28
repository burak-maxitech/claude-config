#!/usr/bin/env bash
# start-claude.sh
# Automates the full Claude Code session startup sequence.
# Usage: ./start-claude.sh [project-name]
# If no project name is provided, prompts interactively.

set -euo pipefail

PROJECTS_ROOT="$HOME/Development/projects"
CONFIG_REPO="$PROJECTS_ROOT/claude-config"

# --- Colors ---
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;37m'
DIM='\033[2m'
CYAN='\033[0;36m'
RESET='\033[0m'

PROJECT_NAME="${1:-}"

# --- Prompt for project name if not provided ---
if [ -z "$PROJECT_NAME" ]; then
    echo -e "\n${CYAN}Available projects:${RESET}"
    find "$PROJECTS_ROOT" -mindepth 1 -maxdepth 1 -type d \
        -exec basename {} \; | sort | while read -r dir; do
        echo -e "  ${GRAY}$dir${RESET}"
    done
    echo ""
    read -rp "Project name: " PROJECT_NAME
    if [ -z "$PROJECT_NAME" ]; then
        echo -e "${RED}No project name provided. Exiting.${RESET}"
        exit 1
    fi
fi

PROJECT_PATH="$PROJECTS_ROOT/$PROJECT_NAME"

if [ ! -d "$PROJECT_PATH" ]; then
    echo -e "${RED}Project not found: $PROJECT_PATH${RESET}"
    exit 1
fi

# --- Step 1: Sync claude-config ---
echo -e "\n${YELLOW}[1/5] Syncing claude-config...${RESET}"
pushd "$CONFIG_REPO" > /dev/null
if git pull --quiet 2>/dev/null; then
    echo -e "  ${GREEN}Config synced.${RESET}"
else
    echo -e "  ${DIM}Warning: Could not pull claude-config. Continuing with local copy.${RESET}"
fi
popd > /dev/null

# --- Step 2: Verify the bx plugin is installed ---
echo -e "${YELLOW}[2/5] Checking the bx plugin...${RESET}"
if command -v claude > /dev/null 2>&1 && claude plugin list 2>/dev/null | grep -q "bx@burak-tools"; then
    echo -e "  ${GREEN}bx plugin installed${RESET}"
else
    echo -e "  ${DIM}Warning: bx plugin not detected. Skills (/bx:*) may not load.${RESET}"
    echo -e "  ${GRAY}Fix (in Claude Code): /plugin marketplace add $CONFIG_REPO${RESET}"
    echo -e "  ${GRAY}                      /plugin install bx@burak-tools${RESET}"
fi

# Check user settings for skill-breaking flags
SETTINGS_FILE="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ] && command -v jq > /dev/null 2>&1; then
    if [ "$(jq -r '.disableSkillShellExecution // false' "$SETTINGS_FILE" 2>/dev/null)" = "true" ]; then
        echo -e "  ${RED}Warning: disableSkillShellExecution=true in ~/.claude/settings.json${RESET}"
        echo -e "  ${GRAY}Breaks /bx:clean --fix, /bx:review --verify, and /bx:resume deep.${RESET}"
        echo -e "  ${GRAY}Fix: set it to false or remove the key.${RESET}"
    fi
fi

# --- Step 3: Navigate to project and pull ---
echo -e "${YELLOW}[3/5] Opening project: $PROJECT_NAME${RESET}"
cd "$PROJECT_PATH"

if [ -d ".git" ]; then
    echo -e "  ${GRAY}Pulling latest changes...${RESET}"
    if git pull --quiet 2>/dev/null; then
        echo -e "  ${GREEN}Project synced.${RESET}"
    else
        echo -e "  ${DIM}Warning: Could not pull. Continuing with local state.${RESET}"
    fi
else
    echo -e "  ${GRAY}Not a git repo — skipping pull.${RESET}"
fi

# --- Step 4: Update Claude Code ---
echo -e "${YELLOW}[4/5] Checking for Claude Code updates...${RESET}"
if claude update 2>&1 | while read -r line; do echo -e "  ${GRAY}$line${RESET}"; done; then
    :
else
    echo -e "  ${DIM}Warning: Could not check for updates.${RESET}"
fi

# --- Step 5: Launch Claude Code with /bx-resume ---
echo -e "${YELLOW}[5/5] Launching Claude Code...${RESET}"
echo -e "  ${GRAY}Tip: Run /bx-resume to get up to speed.${RESET}"
echo ""
claude