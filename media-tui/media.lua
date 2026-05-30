#!/usr/bin/env lua
-- Functional Inline Media Controller (Pure Reactive Lua Version)

-- Initialize the state table at the top to completely isolate it from execution returns
state = {
    first_run = true,
    active_player = ""
}

-- 1. Base command executor helper
local function run_cmd(cmd)
    local handle = io.popen(cmd .. " 2>/dev/null")
    if not handle then return "" end
    local result = handle:read("*a")
    handle:close()
    -- Wrapping in parentheses forces Lua to discard gsub's second return value (match count)
    return (result:gsub("^%s*(.-)%s*$", "%1"))
end

-- Check dependencies
if run_cmd("command -v playerctl") == "" then
    print(" \27[1;31mError:\27[0m playerctl is not installed.")
    os.exit(1)
end

-- Terminal setup: hide cursor and disable canonical input mode
io.write("\27[?25l")
io.flush()
os.execute("stty -icanon -echo min 1 time 0 2>/dev/null")

-- 2. Frame rendering logic
local function render_frame()
    local status = run_cmd("playerctl status")
    
    if status == "" then
        if state.first_run then
            print(" \27[90m♫ Idle\27[0m")
            print(" \27[90m[ No active system media player detected ]\27[0m")
        else
            io.write("\27[2A\27[K")
            print(" \27[90m♫ Idle\27[0m")
            print(" \27[90m[ No active system media player detected ]\27[0m\27[K")
        end
        state.first_run = false
    else
        state.active_player = run_cmd("playerctl -l | head -n 1")
        local title = run_cmd("playerctl metadata title")
        local artist = run_cmd("playerctl metadata artist")

        local track_string = title
        if artist ~= "" then
            track_string = artist .. " - " .. title
        end

        -- Clean up stream platforms strings using patterns
        track_string = track_string:gsub(" %- YouTube", ""):gsub(" %- YouTube Music", ""):gsub(" %- Spotify", "")

        -- Dynamic string truncation based on window columns
        local term_width = tonumber(run_cmd("tput cols")) or 80
        local max_len = term_width - 12
        if #track_string > max_len then
            track_string = track_string:sub(1, max_len - 3) .. "..."
        end

        -- Pull native WirePlumber system volume
        local vol_pct = "100"
        local wp_out = run_cmd("wpctl get-volume @DEFAULT_AUDIO_SINK@")
        local raw_vol = wp_out:match("Volume:%s*([0-9%.]+)")
        if raw_vol then
            vol_pct = tostring(math.floor(tonumber(raw_vol) * 100))
        end

        -- Badge string configuration 
        local status_badge = "\27[1;42;30m Paused \27[0m"
        if status == "Playing" then
            status_badge = "\27[1;45;30m Playing \27[0m"
        end

        -- Render frame lines cleanly
        if not state.first_run then
            io.write("\27[2A") -- Move up 2 lines
        end
        state.first_run = false

        io.write(" \27[1;32m♫\27[0m \27[1m" .. track_string .. "\27[0m\27[K\n")
        io.write(" \27[90mVOL:\27[0m " .. vol_pct .. "%  │  \27[90mSRC:\27[0m " .. (state.active_player:match("^([^%.]+)") or "") .. "  │  " .. status_badge .. "\27[K\n")
    end
    io.flush()
end

-- 3. Clean terminal exit handler
local function cleanup()
    io.write("\27[?25h") -- Show cursor
    os.execute("stty sane 2>/dev/null")
    io.write("\27[2A\27[J") -- Clean lines back to prompt loop
    io.flush()
    os.exit(0)
end

-- Initial Render Frame Core Action
render_frame()

-- Main Input Event Listen Processing Loop
while true do
    local key = io.read(1) -- Halts natively until a key is tapped
    
    if key == " " then
        if run_cmd("playerctl status") ~= "" then
            if state.active_player:find("spotify") and run_cmd("command -v xdotool") ~= "" then
                os.execute("xdotool key XF86AudioPlay")
            else
                os.execute("playerctl play-pause")
            end
        end
    elseif key == "+" or key == "=" then
        os.execute("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+")
    elseif key == "-" then
        os.execute("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")
    elseif key == "n" or key == "N" then
        os.execute("playerctl next 2>/dev/null")
    elseif key == "p" or key == "P" then
        os.execute("playerctl position 0 2>/dev/null && playerctl previous 2>/dev/null")
    elseif key == "q" or key == "Q" or key == "\27" then
        cleanup()
    end

    os.execute("sleep 0.05")
    render_frame()
end
