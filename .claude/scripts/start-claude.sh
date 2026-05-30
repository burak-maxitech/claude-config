#!/usr/bin/env bash
# start-claude.sh
# Automates the full Claude Code session startup sequence.
# Usage: ./start-claude.sh [project-name]   (no name → interactive project picker)
#
# NOTE: the bx toolkit is now a Claude Code PLUGIN (bx@burak-tools), not symlinks.
# Step 1 refreshes the plugin from the GitHub marketplace so every launch has the
# latest skills — the plugin-model equivalent of the old "git pull updates symlinks".
# (Don't want auto-updates? Delete the two `claude plugin ...` lines in Step 1.)

set -uo pipefail

PROJECTS_ROOT="$HOME/Development/projects"
CONFIG_REPO="$PROJECTS_ROOT/claude-config"

# --- Colors ---
YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'
GRAY='\033[0;37m'; DIM='\033[2m'; CYAN='\033[0;36m'; RESET='\033[0m'

PROJECT_NAME="${1:-}"

# --- Project picker (numbered selection if no name given) ---
if [ -z "$PROJECT_NAME" ]; then
    # Build a sorted array of project directory names (bash 3.2-safe — no mapfile)
    projects=()
    while IFS= read -r dir; do
        projects+=("$dir")
    done < <(find "$PROJECTS_ROOT" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)

    if [ "${#projects[@]}" -eq 0 ]; then
        echo -e "${RED}No projects found in $PROJECTS_ROOT. Exiting.${RESET}"
        exit 1
    fi

    echo -e "\n${CYAN}Which project do you want to work on today?${RESET}"
    i=1
    for p in "${projects[@]}"; do
        echo -e "  ${GRAY}${i}-${p}${RESET}"
        i=$((i + 1))
    done
    echo ""
    read -rp "Enter number: " sel

    if [[ "$sel" =~ ^[0-9]+$ ]] && [ "$sel" -ge 1 ] && [ "$sel" -le "${#projects[@]}" ]; then
        PROJECT_NAME="${projects[$((sel - 1))]}"
    elif [ -n "$sel" ] && [ -d "$PROJECTS_ROOT/$sel" ]; then
        PROJECT_NAME="$sel"   # typed a name instead of a number — accept it
    else
        echo -e "${RED}Invalid selection: '$sel'. Exiting.${RESET}"
        exit 1
    fi
fi

PROJECT_PATH="$PROJECTS_ROOT/$PROJECT_NAME"
[ -d "$PROJECT_PATH" ] || { echo -e "${RED}Project not found: $PROJECT_PATH${RESET}"; exit 1; }

# --- Step 1: Sync the bx toolkit (dev clone + installed plugin) ---
echo -e "\n${YELLOW}[1/5] Syncing bx toolkit...${RESET}"
# 1a. Refresh the local dev clone if present (only matters when you edit skills)
# Show the diffstat (drop --quiet) and let errors through (drop 2>/dev/null) so a
# failed pull is visible instead of silently reported as "synced".
if [ -d "$CONFIG_REPO/.git" ]; then
    if git -C "$CONFIG_REPO" pull --stat; then
        echo -e "  ${GREEN}claude-config clone synced.${RESET}"
    else
        echo -e "  ${DIM}Could not pull claude-config clone (continuing).${RESET}"
    fi
fi
# 1b. Refresh the installed plugin from the GitHub marketplace (this is the live skills)
if command -v claude > /dev/null 2>&1 && claude plugin list 2>/dev/null | grep -q "bx@burak-tools"; then
    claude plugin marketplace update burak-tools > /dev/null 2>&1 || true
    claude plugin update bx > /dev/null 2>&1 || true
    echo -e "  ${GREEN}bx plugin up to date.${RESET}"
fi

# --- Step 2: Verify the bx plugin + skill-breaking settings ---
echo -e "${YELLOW}[2/5] Checking the bx plugin...${RESET}"
if command -v claude > /dev/null 2>&1 && claude plugin list 2>/dev/null | grep -q "bx@burak-tools"; then
    echo -e "  ${GREEN}bx plugin installed (skills: /bx:*)${RESET}"
else
    echo -e "  ${DIM}Warning: bx plugin not detected. Skills (/bx:*) may not load.${RESET}"
    echo -e "  ${GRAY}Fix (in Claude Code): /plugin marketplace add burak-maxitech/claude-config${RESET}"
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
    if git pull --stat; then
        echo -e "  ${GREEN}Project synced.${RESET}"
    else
        echo -e "  ${DIM}Could not pull (continuing with local state).${RESET}"
    fi
else
    echo -e "  ${GRAY}Not a git repo — skipping pull.${RESET}"
fi

# --- Step 4: Update Claude Code ---
echo -e "${YELLOW}[4/5] Checking for Claude Code updates...${RESET}"
if ! claude update 2>&1 | while read -r line; do echo -e "  ${GRAY}$line${RESET}"; done; then
    echo -e "  ${DIM}Could not check for updates.${RESET}"
fi

# --- Step 5: Launch Claude Code ---
echo -e "${YELLOW}[5/5] Launching Claude Code...${RESET}"
echo -e "  ${GRAY}Tip: run /bx:resume to get up to speed.${RESET}"
echo ""
claude
