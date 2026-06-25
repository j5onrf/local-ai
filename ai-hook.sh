#!/usr/bin/env bash
# Local-Ai Agent Hook v0.8.8.16 [j5onrf] [06-25-26]

# Exit immediately if the shell is non-interactive
[[ $- != *i* ]] && return

_AI_DIR="$HOME/.config/local-ai"
_AI_SCRIPT_PATH="$_AI_DIR/ai-agent.py"
[[ -f "$_AI_SCRIPT_PATH" ]] || return

# Resolve python3 natively without spawning a subshell fork on shell startup
command -v python3 >/dev/null 2>&1 && _AI_PYTHON_BIN="python3" || _AI_PYTHON_BIN="python"

# Quietly clean up orphaned active_cd files from dead PIDs on shell startup
for _f in "$_AI_DIR"/.active_cd.*; do
    if [[ -f "$_f" ]]; then
        _pid="${_f##*.active_cd.}"
        # If the process is no longer running, delete the stale teleport file safely
        kill -0 "$_pid" 2>/dev/null || rm -f "$_f"
    fi
done

# Teleport Hook (With strict exit-code preservation, single-append guard, and PID isolation)
_ai_teleport() {
    local exit_code=$?
    local active_file="$_AI_DIR/.active_cd.$$"
    [ -f "$active_file" ] && { cd "$(<"$active_file")"; rm -f "$active_file"; }
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
        
        # Write target directory path to active teleport file isolated by shell PID
        echo "$target_path" > "$_AI_DIR/.active_cd.$$"
        
        local proj_name=$(basename "$target_path")
        local context_file="$target_path/index-map-${proj_name}.txt"
        
        # Compile the SmartCrusher AST map directly inside the project directory
        "$_AI_PYTHON_BIN" "$_AI_DIR/tools/map/index-map" "$target_path" || return 1
        
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
