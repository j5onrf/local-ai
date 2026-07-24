#!/usr/bin/env bash
# Production Local-AI Shell Hook v0.9.5.5

[[ $- != *i* || ! -f "$HOME/.config/local-ai/ai-agent.py" ]] && return
_AI_DIR="$HOME/.config/local-ai"
_AI_PY=$(command -v python3 || command -v python)

_ai_teleport() {
    local f="$_AI_DIR/.active_cd.$$"
    if [[ -f "$f" ]]; then
        local target=$(<"$f")
        rm -f "$f"
        [[ -d "$target" ]] && cd "$target"
    fi
    # Auto garbage-collect orphaned .active_cd files from closed or dead shell PIDs
    local old_f pid
    for old_f in "$_AI_DIR"/.active_cd.*; do
        [[ -f "$old_f" ]] || continue
        pid="${old_f##*.active_cd.}"
        kill -0 "$pid" 2>/dev/null || rm -f "$old_f"
    done
}

if [[ -n "$ZSH_VERSION" ]]; then
    autoload -Uz add-zsh-hook 2>/dev/null && add-zsh-hook precmd _ai_teleport
elif [[ "$PROMPT_COMMAND" != *_ai_teleport* ]]; then
    PROMPT_COMMAND="_ai_teleport${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
fi

ai_handle_missing() {
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
        
        echo "$path" > "$_AI_DIR/.active_cd.$$"
        name=$(basename "$path")
        map="$path/index-map-$name.txt"
        db="$path/index-map-memory-$name.db"
        
        { [[ ! -f "$map" || ! -f "$db" || "$path" -nt "$map" ]] || \
          [[ -n "$(find "$path" ! -path "$path" -not -path '*/.git/*' -not -path '*/.agent/*' -not -name 'history.md' ! -name "$(basename "$map")" -newer "$map" -print -quit 2>/dev/null)" ]]; } && {
            "$_AI_PY" "$_AI_DIR/tools/map/index-map" "$path" || { rm -f "$_AI_DIR/.active_cd.$$"; return 1; }
        }
        [[ -f "$map" ]] && AI_ACTIVE_SKILL="${skills[*]}" AI_WORKSPACE_PATH="$path" "$_AI_PY" "$_AI_DIR/ai-agent.py" --talk-chat "$(<"$map")"
        _ai_teleport
    else
        "$_AI_PY" "$_AI_DIR/ai-agent.py" --talk "$@"
    fi
}

view() {
    local f="${1:-}"
    if [[ -z "$f" && (! -t 0 || -p /dev/stdin) ]]; then
        FORCE_COLOR=1 "$_AI_PY" -c "import sys, rich.markdown, rich.console; rich.console.Console().print(rich.markdown.Markdown(sys.stdin.read()))"
    elif [[ -f "$f" && "$f" == *.md ]]; then
        FORCE_COLOR=1 "$_AI_PY" -m rich.markdown "$f"
    else
        cat "$@"
    fi
}
