#!/usr/bin/env bash
# AI Suggestion v0.7.8 [j5onrf] [06-04-26]

[[ $- != *i* ]] && return

_AI_SCRIPT_PATH="$HOME/.config/local-ai/ai-suggestion/alias-ai.py"
[[ ! -f "$_AI_SCRIPT_PATH" ]] && return

_AI_PYTHON_BIN=$(command -v python3 2>/dev/null || type -p python3 2>/dev/null || echo "python3")

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    local intent="$*"
    if [[ -z "$intent" ]]; then
        return 127
    fi

    local cmd
    cmd=$("$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --interactive "$intent")
    if [[ -n "$cmd" ]]; then
        local expanded_cmd="${cmd/#\~/$HOME}"
        
        if [[ -d "$expanded_cmd" ]]; then
            ai init "$expanded_cmd"
        else
            eval "$cmd"
        fi
    fi
}

command_not_found_handle() {
    if [[ "$1" == --* ]]; then
        return 127
    fi
    ai_handle_missing "$*"
    return 0
}

command_not_found_handler() {
    command_not_found_handle "$@"
}

ai() {
    local projects_dir="/home/j5/.config/local-ai/ai-suggestion/projects"
    local tool_bin="/home/j5/.config/local-ai/ai-suggestion/tools/init-projects"

    if [[ "$1" == "init" ]]; then
        local target_path="$2"
        local skill_name="${3:-}" # Captures the skill name dynamically from the context mapping

        if [[ -z "$target_path" ]]; then
            target_path=$(pwd)
        fi
        target_path=$(cd "$target_path" && pwd)

        local safe_name="${target_path//\//-}"
        safe_name="${safe_name#-}"
        local context_file="$projects_dir/${safe_name}.txt"

        # Pass target path and skill name directly to the compiler script
        "$tool_bin" "$target_path" "$skill_name"
        if [ $? -ne 0 ]; then
            return 1 
        fi

        local payload=$(cat "$context_file")
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$payload"
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
