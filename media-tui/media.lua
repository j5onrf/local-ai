#!/usr/bin/env lua
-- ==========================================================================
-- Tool: media-tui (Interactive Inline Variant)
-- Controls: [Space] Pause/Play | [- / + / =] Volume | [q] Quit / [Ctrl+C] Clean Exit
-- ==========================================================================

-- Helper to execute background terminal commands silently
local function exec_cmd(cmd)
    local handle = io.popen(cmd .. " 2>/dev/null")
    if not handle then return "" end
    local output = handle:read("*a")
    handle:close()
    return output or ""
end

-- 1. Gather Media Info & System States
local function get_system_states()
    local vol = "0%"
    local src = "none"
    local state = "Stopped"
    local title = nil

    -- Capture Volume
    local wp_out = exec_cmd("wpctl get-volume @DEFAULT_AUDIO_SINK@")
    if wp_out ~= "" then
        local volume_num = wp_out:match("Volume:%s+(%d%.%d+)")
        local is_muted = wp_out:match("%[MUTED%]")
        if is_muted then vol = "MUTED" elseif volume_num then vol = math.floor(tonumber(volume_num) * 100) .. "%" end
    end

    -- Capture Player Status
    local player_check = exec_cmd("playerctl -l")
    if player_check ~= "" then
        src = exec_cmd("playerctl metadata --format '{{ playerName }}'"):gsub("%s+", "")
        state = exec_cmd("playerctl status"):gsub("%s+", "")
        local meta = exec_cmd("playerctl metadata --format '{{ artist }} - {{ title }}'")
        title = meta:gsub("^%s*(.-)%s*$", "%1")
        if title == "" or title == "-" then title = nil end
    end

    return vol, src, state, title
end

-- 2. Render Layout Inline (Clearing previous lines to prevent scrolling)
local function draw_tui()
    local volume, source, state, title = get_system_states()

    local status_tag = state
    if state == "Playing" then
        status_tag = "\27[1;32mPlaying\27[0m"
    elseif state == "Paused" then
        status_tag = "\27[7;33m Paused \27[0m"
    end

    -- ANSI Escape codes: Clear current line, draw, go down, clear, draw, go up
    if title then
        io.write(string.format("\27[2K\r ♫ %s\n", title))
    else
        io.write("\27[2K\r 🎵\n")
    end
    
    io.write(string.format("\27[2K\r VOL: %-4s │  SRC: %-5s │  %s\r", volume, source, status_tag))
    io.write("\27[1A") -- Move cursor back up 1 line to stay locked in position
    io.flush()
end

-- 3. Live Keyboard Control Loop
local function run_loop()
    -- Configure terminal to read single raw keystrokes instantly
    os.execute("stty -icanon -echo min 0 time 1")
    
    -- Hide the hardware terminal cursor completely
    io.write("\27[?25l")
    io.flush()

    -- Initial layout paint
    draw_tui()

    local last_update = os.time()

    while true do
        local char = io.read(1)

        if char == " " then
            -- Spacebar: Toggle play/pause
            exec_cmd("playerctl play-pause")
            draw_tui()
        elseif char == "-" then
            -- Minus Key: Lower volume by 5%
            exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")
            draw_tui()
        elseif char == "+" or char == "=" then
            -- Plus/Equal Key: Raise volume by 5%
            exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+")
            draw_tui()
        elseif char == "q" or char == "Q" then
            break
        end

        -- Refresh stats automatically once every second
        local current_time = os.time()
        if current_time - last_update >= 1 then
            draw_tui()
            last_update = current_time
        end
    end
end

-- 4. Clean Global Shutdown Routine
local function cleanup()
    -- Restore original terminal settings
    os.execute("stty sane")
    -- Show the hardware terminal cursor again
    io.write("\27[?25h")
    -- Move past the layout frame for a clean terminal prompt
    print("\n\n")
end

-- Run the engine
local status = pcall(run_loop)
cleanup()

if not status then
    os.exit(0)
end
