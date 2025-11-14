#!/bin/bash
#
# Install git hooks for ccopilot
#
# This script copies hook templates from scripts/git-hooks/ to .git/hooks/
# and makes them executable.
#
# Usage:
#   ./scripts/install-hooks.sh [--force]
#
# Options:
#   --force    Overwrite existing hooks without prompting
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FORCE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=1
            shift
            ;;
        *)
            echo "${RED}Unknown option: $1${NC}" >&2
            echo "Usage: $0 [--force]" >&2
            exit 1
            ;;
    esac
done

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "${RED}Error: Not in a git repository${NC}" >&2
    echo "Please run this script from the repository root" >&2
    exit 1
fi

# Check if hooks directory exists
if [ ! -d scripts/git-hooks ]; then
    echo "${RED}Error: scripts/git-hooks directory not found${NC}" >&2
    exit 1
fi

echo "${BLUE}=== Installing Git Hooks ===${NC}"
echo ""

# List of hooks to install
HOOKS=(
    "pre-commit"
    "commit-msg"
    "pre-push"
    "post-merge"
)

INSTALLED=0
SKIPPED=0

for hook in "${HOOKS[@]}"; do
    SOURCE="scripts/git-hooks/$hook"
    TARGET=".git/hooks/$hook"

    if [ ! -f "$SOURCE" ]; then
        echo "${YELLOW}[skip]${NC} $hook (template not found)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Check if hook already exists
    if [ -f "$TARGET" ]; then
        if [ $FORCE -eq 0 ]; then
            echo "${YELLOW}[exists]${NC} $hook already exists"
            read -p "Overwrite? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "${YELLOW}[skip]${NC} $hook (keeping existing)"
                SKIPPED=$((SKIPPED + 1))
                continue
            fi
        fi
    fi

    # Copy and make executable
    cp "$SOURCE" "$TARGET"
    chmod +x "$TARGET"
    echo "${GREEN}[install]${NC} $hook"
    INSTALLED=$((INSTALLED + 1))
done

echo ""
echo "${BLUE}=== Summary ===${NC}"
echo "Installed: $INSTALLED"
echo "Skipped:   $SKIPPED"
echo ""

if [ $INSTALLED -gt 0 ]; then
    echo "${GREEN}Git hooks installed successfully!${NC}"
    echo ""
    echo "Installed hooks:"
    for hook in "${HOOKS[@]}"; do
        if [ -f ".git/hooks/$hook" ]; then
            echo "  - $hook"
        fi
    done
    echo ""
    echo "To disable a hook, remove or rename the file in .git/hooks/"
    echo "To update hooks, run this script again with --force"
else
    echo "${YELLOW}No hooks were installed${NC}"
fi

echo ""
echo "${BLUE}=== Optional Tools ===${NC}"
echo "The hooks use the following optional tools:"
echo "  - ruff:     Python formatting and linting (required)"
echo "  - prettier: Markdown/YAML/JSON formatting (optional)"
echo "  - ast-grep: Structural code search (optional)"
echo "  - fastmod:  Code refactoring (optional)"
echo "  - sg:       Semantic grep (optional)"
echo ""
echo "Install missing tools:"
echo "  brew install ruff ast-grep"
echo "  brew install prettier  # or: npm install -g prettier"
echo "  cargo install fastmod"
echo ""

# Check tool availability
echo "${BLUE}=== Tool Availability ===${NC}"
command -v ruff >/dev/null 2>&1 && echo "${GREEN}[found]${NC} ruff" || echo "${RED}[missing]${NC} ruff"
command -v prettier >/dev/null 2>&1 && echo "${GREEN}[found]${NC} prettier" || echo "${YELLOW}[optional]${NC} prettier"
command -v ast-grep >/dev/null 2>&1 && echo "${GREEN}[found]${NC} ast-grep" || echo "${YELLOW}[optional]${NC} ast-grep"
command -v fastmod >/dev/null 2>&1 && echo "${GREEN}[found]${NC} fastmod" || echo "${YELLOW}[optional]${NC} fastmod"
command -v sg >/dev/null 2>&1 && echo "${GREEN}[found]${NC} sg" || echo "${YELLOW}[optional]${NC} sg"
command -v bd >/dev/null 2>&1 && echo "${GREEN}[found]${NC} bd" || echo "${YELLOW}[optional]${NC} bd"

exit 0
