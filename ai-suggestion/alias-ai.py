import sys
import re
import requests
import os

CONTEXT_FILE = "/home/j5/.config/local-iq/ai-suggestion/ai-context.txt"

# ==============================================================================
# INLINE LEARNING MODE (--learn)
# ==============================================================================
if len(sys.argv) > 1 and sys.argv[1] == "--learn":
    if len(sys.argv) < 4:
        print("ERROR: Missing arguments for learning.")
        sys.exit(1)
        
    target_cmd = sys.argv[2].strip()
    new_intent = sys.argv[3].strip()
    
    try:
        with open(CONTEXT_FILE, "r") as f:
            lines = f.readlines()
            
        cmd_found = False
        updated_lines = []
        
        for line in lines:
            # Look for an exact command match to append the new intent inline
            if "--->" in line and line.strip().startswith(target_cmd):
                left_side, right_side = line.split("--->", 1)
                if left_side.strip() == target_cmd:
                    cmd_found = True
                    existing_intents = [i.strip() for i in right_side.split(",")]
                    if new_intent not in existing_intents:
                        existing_intents.append(new_intent)
                    line = f"{target_cmd} ---> {', '.join(existing_intents)}\n"
            updated_lines.append(line)
            
        # If it's a completely new command, add it to the bottom
        if not cmd_found:
            if updated_lines and not updated_lines[-1].endswith("\n"):
                updated_lines[-1] += "\n"
            updated_lines.append(f"{target_cmd} ---> {new_intent}\n")
            
        with open(CONTEXT_FILE, "w") as f:
            f.writelines(updated_lines)
            
        print("SUCCESS")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

# ==============================================================================
# STANDARD TRANSLATION LOOKUP MODE
# ==============================================================================
user_input = sys.argv[1] if len(sys.argv) > 1 else ""
if not user_input:
    print("UNKNOWN_COMMAND")
    sys.exit(0)

try:
    with open(CONTEXT_FILE, "r") as f:
        system_context = f.read().strip()
except Exception:
    print("UNKNOWN_COMMAND")
    sys.exit(1)

formatted_prompt = (
    f"<|im_start|>system\n{system_context}\n<|im_end|>\n"
    f"<|im_start|>user\n{user_input}\n<|im_end|>\n"
    f"<|im_start|>assistant\n"
)

payload = {
    "prompt": formatted_prompt,
    "stream": False,
    "cache_prompt": True
}

try:
    response = requests.post("http://localhost:8080/completion", json=payload, timeout=5)
    raw_result = response.json()["content"].strip()
    
    # Text Sanitation Layer
    clean_result = re.sub(r"<think>.*?</think>", "", raw_result, flags=re.DOTALL).strip()
    clean_result = re.sub(r"^cmd:\s*", "", clean_result)
    clean_result = clean_result.split("--->")[0].strip()
    clean_result = re.split(r"(You are a|Rules:|# ==|# ---)", clean_result)[0].strip()
    
    # Catch structural failures or explicit model omissions
    if "ERROR" in clean_result or "not found" in clean_result or "UNKNOWN_COMMAND" in clean_result or not clean_result:
        print("UNKNOWN_COMMAND")
    else:
        print(clean_result)
except Exception:
    print("UNKNOWN_COMMAND")
