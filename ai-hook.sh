#!/usr/bin/env bash
# Unveiled Production Shell Hook v0.9.42

[[ $- != *i* || ! -f "$HOME/.config/local-ai/ai-agent.py" ]] && return
_AI_DIR="$HOME/.config/local-ai"
_AI_PY=$(command -v python3 || command -v python)

_ai_teleport() {
    local rc=$? f="$_AI_DIR/.active_cd.$$"
    [[ -f "$f" ]] && { cd "$(<"$f")" && rm -f "$f"; }
    return $rc
}

if [[ -n "$ZSH_VERSION" ]]; then
    autoload -Uz add-zsh-hook 2>/dev/null && add-zsh-hook precmd _ai_teleport
elif [[ "$PROMPT_COMMAND" != *_ai_teleport* ]]; then
    PROMPT_COMMAND="_ai_teleport${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
fi

ai_handle_missing() {
    [[ -n "$ZSH_VERSION" ]] && setopt local_options ksh_arrays
    [[ -z "$*" ]] && return 127
    local cmd=$("$_AI_PY" "$_AI_DIR/ai-agent.py" --interactive "$*")
    [[ -z "$cmd" ]] && return 127
    local exp="${cmd/#\~/$HOME}"
    [[ -d "$exp" ]] && ai init "$exp" || eval "$cmd"
}
command_not_found_handle() { [[ "$1" != --* ]] && ai_handle_missing "$*"; }
command_not_found_handler() { command_not_found_handle "$@"; }

ai() {
    if [[ "$1" == "init" ]]; then
        local path=$(pwd) skills=() name map db
        [[ -n "${2:-}" && "${2:-}" != -* ]] && { path="$2"; skills=("${@:3}"); } || skills=("${@:2}")
        mkdir -p "$path" || return 1
        path=$(CDPATH= cd "$path" && pwd -P) || return 1
        
        # Cleanup stale active_cd files asynchronously
        (for f in "$_AI_DIR"/.active_cd.*; do
            [[ -f "$f" ]] && { kill -0 "${f##*.active_cd.}" 2>/dev/null || rm -f "$f"; }
        done) &>/dev/null &
        
        echo "$path" > "$_AI_DIR/.active_cd.$$"
        name=$(basename "$path")
        map="$path/index-map-$name.txt"
        db="$path/index-map-memory-$name.db"
        
        { [[ ! -f "$map" || ! -f "$db" || "$path" -nt "$map" ]] || \
          [[ -n "$(find "$path" ! -path "$path" -not -path '*/.git/*' -not -path '*/.agent/*' -not -name 'history.md' ! -name "$(basename "$map")" -newer "$map" -print -quit 2>/dev/null)" ]]; } && {
            "$_AI_PY" "$_AI_DIR/tools/map/index-map" "$path" || return 1
        }
        [[ -f "$map" ]] && AI_ACTIVE_SKILL="${skills[*]}" AI_WORKSPACE_PATH="$path" "$_AI_PY" "$_AI_DIR/ai-agent.py" --talk-chat "$(<"$map")" || \
        { printf "\033[1;31mError: Context file not found at: %s\033[0m\n" "$map" >&2; return 1; }
    else
        "$_AI_PY" "$_AI_DIR/ai-agent.py" --talk "$@"
    fi
}

view() {
    local f="${1:-}"
    if [[ -z "$f" ]]; then
        if [[ -p /dev/stdin || ! -t 0 ]]; then
            FORCE_COLOR=1 "$_AI_PY" -c "import sys; from rich.console import Console; from rich.markdown import Markdown; Console().print(Markdown(sys.stdin.read()))"
        else
            return 0
        fi
    elif [[ -f "$f" && "$f" == *.md ]]; then
        FORCE_COLOR=1 "$_AI_PY" -m rich.markdown "$f"
    else
        cat "$@"
    fi
}
