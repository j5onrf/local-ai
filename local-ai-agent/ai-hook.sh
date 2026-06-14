#!/usr/bin/env bash
# Local-Ai Agent Hook v0.8.3.5 [j5onrf] [06-14-26]

# Exit immediately if the shell is non-interactive
[[ $- != *i* ]] && return

_AI_SCRIPT_PATH="$HOME/.config/local-ai/local-ai-agent/alias-ai.py"
[[ ! -f "$_AI_SCRIPT_PATH" ]] && return

# Optimized: resolve python3 natively without spawning a subshell fork on shell startup
if command -v python3 >/dev/null 2>&1; then
    _AI_PYTHON_BIN="python3"
else
    _AI_PYTHON_BIN="python"
fi

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    [[ -z "$*" ]] && return 127
    
    # Decouple local declaration from assignment to preserve command exit status in $?
    local cmd
    cmd=$("$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --interactive "$*")
    
    if [[ -n "$cmd" ]]; then
        local exp="${cmd/#\~/$HOME}"
        if [[ -d "$exp" ]]; then
            ai init "$exp"
        else
            eval "$cmd"
        fi
    else
        # Return 127 to let the shell natively print standard "command not found" warnings
        return 127
    fi
}

command_not_found_handle() {
    [[ "$1" == --* ]] && return 127
    ai_handle_missing "$*"
}
command_not_found_handler() { command_not_found_handle "$@"; }

ai() {
    local projects_dir="$HOME/.config/local-ai/local-ai-agent/projects"
    local tool_bin="$HOME/.config/local-ai/local-ai-agent/tools/init-projects"

    if [[ "$1" == "init" ]]; then
        local target_path="" skill_name=""
        if [[ -d "${2:-}" ]]; then
            target_path="$2"
            skill_name="${3:-}"
        else
            target_path=$(pwd)
            skill_name="${2:-}"
        fi

        # Safeguard: prevent target_path contamination if CDPATH is configured
        target_path=$(CDPATH= cd "$target_path" && pwd) || return 1
        local safe_name="${target_path//\//-}"
        local context_file="$projects_dir/${safe_name#-}.txt"

        # Blind pass-through of raw arguments
        "$tool_bin" "$target_path" "$skill_name" || return 1
        
        # Optimized: read context_file directly with $(<file) instead of spawning 'cat'
        if [[ -f "$context_file" ]]; then
            AI_ACTIVE_SKILL="$skill_name" "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$(<"$context_file")"
        else
            sys.stderr.write "\033[1;31mError: Context file not found at: $context_file\033[0m\n"
            return 1
        fi
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
