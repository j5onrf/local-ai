#!/usr/bin/env bash
# Local-Ai Agent Hook v0.8.8.8 [j5onrf] [06-24-26]

# 1. Scope Guard: Exit immediately if the shell is non-interactive
[[ $- != *i* ]] && return

_AI_DIR="$HOME/.config/local-ai"
_AI_SCRIPT_PATH="$_AI_DIR/ai-agent.py"
[[ -f "$_AI_SCRIPT_PATH" ]] || return

# Resolve python3 natively without spawning a subshell fork on shell startup
command -v python3 >/dev/null 2>&1 && _AI_PYTHON_BIN="python3" || _AI_PYTHON_BIN="python"

# 2. Teleport Hook (With strict exit-code preservation & single-append guard)
_ai_teleport() {
    local exit_code=$?
    [ -f "$_AI_DIR/.active_cd" ] && { cd "$(<"$_AI_DIR/.active_cd")"; rm -f "$_AI_DIR/.active_cd"; }
    return $exit_code
}

# Prevent duplicate appends to PROMPT_COMMAND when sourcing .bashrc multiple times
if [[ "$PROMPT_COMMAND" != *_ai_teleport* ]]; then
    PROMPT_COMMAND="_ai_teleport${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
fi

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    [[ -z "$*" ]] && return 127
    local cmd; cmd=$("$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --interactive "$*")
    [[ -z "$cmd" ]] && return 127
    local exp="${cmd/#\~/$HOME}"
    [[ -d "$exp" ]] && ai init "$exp" || eval "$cmd"
}

command_not_found_handle() { [[ "$1" == --* ]] && return 127; ai_handle_missing "$*"; }
command_not_found_handler() { command_not_found_handle "$@"; }

ai() {
    if [[ "$1" == "init" ]]; then
        local target_path=$(pwd) skill_name="${2:-}"
        [[ -d "${2:-}" ]] && target_path="$2" && skill_name="${3:-}"
        target_path=$(CDPATH= cd "$target_path" && pwd) || return 1
        
        # Write target directory path to active teleport file
        echo "$target_path" > "$_AI_DIR/.active_cd"
        
        local safe_name="${target_path//\//-}"
        local context_file="$_AI_DIR/projects/project-init/${safe_name#-}.txt"
        "$_AI_DIR/tools/init-projects" "$target_path" "$skill_name" || return 1
        if [[ -f "$context_file" ]]; then
            AI_ACTIVE_SKILL="$skill_name" AI_WORKSPACE_PATH="$target_path" "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$(<"$context_file")"
        else
            printf "\033[1;31mError: Context file not found at: %s\033[0m\n" "$context_file" >&2
            return 1
        fi
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
