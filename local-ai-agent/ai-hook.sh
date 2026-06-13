#!/usr/bin/env bash
# Local-Ai Agent Hook v0.8.4.0 [j5onrf] [06-12-26]

# Exit immediately if the shell is non-interactive
[[ $- != *i* ]] && return

_AI_SCRIPT_PATH="$HOME/.config/local-ai/local-ai-agent/alias-ai.py"
[[ ! -f "$_AI_SCRIPT_PATH" ]] && return
_AI_PYTHON_BIN=$(command -v python3 2>/dev/null || type -p python3 2>/dev/null || echo "python3")

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    [[ -z "$*" ]] && return 127
    local cmd=$("$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --interactive "$*")
    if [[ -n "$cmd" ]]; then
        local exp="${cmd/#\~/$HOME}"
        [[ -d "$exp" ]] && ai init "$exp" || eval "$cmd"
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

        target_path=$(cd "$target_path" && pwd) || return 1
        local safe_name="${target_path//\//-}"
        local context_file="$projects_dir/${safe_name#-}.txt"

        "$tool_bin" "$target_path" "$skill_name" || return 1
        AI_ACTIVE_SKILL="$skill_name" "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$(cat "$context_file")"
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
