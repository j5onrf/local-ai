#!/usr/bin/env bash

# Ensure this script only runs in an interactive shell session
[[ $- != *i* ]] && return

ai_handle_missing() {
    local intent="$*"
    # UPDATED SUBFOLDER PATH:
    local script_path="$HOME/.config/local-iq/ai-suggestion/alias-ai.py"
    local cmd learn_key target_command result key

    if [[ ! -f "$script_path" || -z "$intent" ]]; then
        return 127
    fi

    # 1. Ask the AI if it has a semantic mapping for this phrase
    cmd=$(python3 "$script_path" "$intent")

    # 2. MATCH FOUND: Offer to run it immediately
    if [[ -n "$cmd" && "$cmd" != "UNKNOWN_COMMAND" ]]; then
        echo -e "\e[1;32mAI Suggestion:\e[0m $cmd"
        read -p "Execute [Enter] / Cancel [Any Key]? " -s -n 1 key
        echo
        if [[ -z "$key" ]]; then
            eval "$cmd"
            return 0
        fi
        return 0
    fi

    # 3. NO MATCH FOUND: Agent self-conforms dynamically to the user
    echo -e "\e[1;33mℹ \"$intent\" is not mapping to a known automation.\e[0m"
    read -p "Would you like to teach the agent this custom phrase? (y/N): " -n 1 learn_key
    echo
    
    if [[ "$learn_key" =~ ^[Yy]$ ]]; then
        echo -e "\e[1;34mEnter the exact executable command this should map to:\e[0m"
        read -e -p "❯ " target_command
        
        if [[ -n "$target_command" ]]; then
            # Commit to local memory (ai-context.txt)
            result=$(python3 "$script_path" --learn "$target_command" "$intent")
            
            if [[ "$result" == "SUCCESS" ]]; then
                echo -e "\e[1;32m✓ Memory updated! Running command now...\e[0m"
                eval "$target_command"
                return 0
            else
                echo -e "\e[1;31m$result\e[0m"
                return 1
            fi
        else
            echo "Cancelled. Nothing added to agent memory."
            return 0
        fi
    fi
    return 127
}

# The standard fallback gatekeeper
command_not_found_handle() {
    ai_handle_missing "$*"
    return 127
}

# --- FAST BOOTSTRAP ---
--bootstrap() {
    local bootstrap_script="$HOME/.config/local-iq/ai-suggestion/bootstrap-iq.py"
    if [[ ! -f "$bootstrap_script" ]]; then
        echo -e "\e[1;31m❌ Error: bootstrap-iq.py not found\e[0m"
        return 1
    fi
    local shell_config="$HOME/.${SHELL##*/}"rc
    [[ ! -f "$shell_config" ]] && shell_config="$HOME/.bashrc"
    python3 "$bootstrap_script" "$shell_config"
}
