#!/usr/bin/env bash
# Local-Ai Agent Hook v0.8.3.8 [j5onrf] [06-14-26]

# Exit immediately if the shell is non-interactive
[[ $- != *i* ]] && return

_AI_SCRIPT_PATH="$HOME/.config/local-ai/local-ai-agent/alias-ai.py"
[[ -f "$_AI_SCRIPT_PATH" ]] || return

# Resolve python3 natively without spawning a subshell fork on shell startup
command -v python3 >/dev/null 2>&1 && _AI_PYTHON_BIN="python3" || _AI_PYTHON_BIN="python"

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    [[ -z "$*" ]] && return 127
    local cmd; cmd=$("$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --interactive "$*")
    if [[ -n "$cmd" ]]; then
        local exp="${cmd/#\~/$HOME}"
        [[ -d "$exp" ]] && ai init "$exp" || eval "$cmd"
    else
        return 127
    fi
}

command_not_found_handle() { [[ "$1" == --* ]] && return 127; ai_handle_missing "$*"; }
command_not_found_handler() { command_not_found_handle "$@"; }

ai() {
    local projects_dir="$HOME/.config/local-ai/local-ai-agent/projects"
    local tool_bin="$HOME/.config/local-ai/local-ai-agent/tools/init-projects"
    if [[ "$1" == "init" ]]; then
        local target_path=$(pwd) skill_name="${2:-}"
        [[ -d "${2:-}" ]] && target_path="$2" && skill_name="${3:-}"
        target_path=$(CDPATH= cd "$target_path" && pwd) || return 1
        local safe_name="${target_path//\//-}"
        local context_file="$projects_dir/${safe_name#-}.txt"
        "$tool_bin" "$target_path" "$skill_name" || return 1
        if [[ -f "$context_file" ]]; then
            AI_ACTIVE_SKILL="$skill_name" "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$(<"$context_file")"
        else
            printf "\033[1;31mError: Context file not found at: %s\033[0m\n" "$context_file" >&2
            return 1
        fi
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
