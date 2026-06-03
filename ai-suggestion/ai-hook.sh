#!/usr/bin/env bash
# AI Suggestion v0.7.7.2 [j5onrf] [06-02-26]

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
        # Expand ~ to absolute path to test if it's a directory
        local expanded_cmd="${cmd/#\~/$HOME}"
        
        if [[ -d "$expanded_cmd" ]]; then
            # Direct On-Demand Init: Launch the workspace agent on the target folder
            ai init "$expanded_cmd"
        else
            # Run the command normally
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
        if [[ -z "$target_path" ]]; then
            target_path=$(pwd)
        fi
        target_path=$(cd "$target_path" && pwd)

        # Generate unique path-safe context filename
        local safe_name="${target_path//\//-}"
        safe_name="${safe_name#-}"
        local context_file="$projects_dir/${safe_name}.txt"

        # Execute indexing script
        "$tool_bin" "$target_path"
        if [ $? -ne 0 ]; then
            return 1 
        fi

        local payload=$(cat "$context_file")
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk-chat "$payload"
    else
        "$_AI_PYTHON_BIN" "$_AI_SCRIPT_PATH" --talk "$@"
    fi
}
