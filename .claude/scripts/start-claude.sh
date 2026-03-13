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
        ! -name "claude-config" \
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

# --- Step 2: Verify symlinks ---
echo -e "${YELLOW}[2/5] Checking config symlinks...${RESET}"
FOUND_SYMLINKS=false
for item in "$HOME/.claude"/*; do
    if [ -L "$item" ]; then
        target=$(readlink "$item")
        echo -e "  ${GREEN}$(basename "$item") -> $target${RESET}"
        FOUND_SYMLINKS=true
    fi
done
if [ "$FOUND_SYMLINKS" = false ]; then
    echo -e "  ${DIM}Warning: No symlinks found in ~/.claude. Skills may not load.${RESET}"
    echo -e "  ${GRAY}Fix: ln -s $CONFIG_REPO/commands ~/.claude/commands${RESET}"
    echo -e "  ${GRAY}Fix: ln -s $CONFIG_REPO/skills ~/.claude/skills${RESET}"
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

# --- Step 5: Launch Claude Code with /resume-work ---
echo -e "${YELLOW}[5/5] Launching Claude Code...${RESET}"
echo ""
claude -p "/resume-work"
