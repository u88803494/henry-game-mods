--[[--------------------------------------------------------------------------
    hecatomb_reminder

    Nudges you when a hecatomb or prayer is available but hasn't been used.

    The game already decides whether you can afford one: the action button in
    the gods panel sits in state "active" exactly when the action is available.
    We read that state rather than recomputing costs, so the mod can't disagree
    with the game.

    Loaded by lib_mod_loader: any file under script/campaign/main_troy/mod/ is
    executed, then a function named after the file is called. Hence the name of
    this file must stay in sync with the function at the bottom.
----------------------------------------------------------------------------]]

local PANEL = "gods_and_favor"
local HOLDER = "container_hecatomb_prayer"

-- UI paths, confirmed against troy_constants.lua's tutorial script.
local ACTIONS = {
    hecatomb = {holder = "hecatomb_holder", label = "百牲祭"},
    prayer   = {holder = "prayer_holder",   label = "祈禱"},
}

-- Remind again this many turns after the last hecatomb, even when the gods
-- panel is closed and we cannot read the button state.
local REMIND_AFTER_TURNS = 5

local SAVED_LAST_HECATOMB = "hecatomb_reminder_last_turn"

local GODS = {
    "aphrodite", "apollo", "ares", "artemis", "athena",
    "hephaestus", "hera", "poseidon", "zeus",
}

-- campaign_gods_attitude_tiers: tier_0 caps at 49, tier_1 at 299, tier_2 at 599.
local TIER_CAPS = {49, 299, 599}


local function log(text)
    local line = "[hecatomb_reminder] " .. tostring(text)
    out(line)
    if ModLog then ModLog(line) end
end


--- Returns the action button uicomponent, or false when the panel is closed.
--  find_uicomponent returns false (not nil) when any step of the path misses.
local function action_button(action)
    local root = core:get_ui_root()
    if not root then return false end
    return find_uicomponent(root, PANEL, HOLDER, ACTIONS[action].holder, "action_button")
end


--- true / false when the panel is readable, nil when it is not open.
local function is_available(action)
    local button = action_button(action)
    if not button then return nil end
    return button:CurrentState() == "active"
end


local function tier_of(attitude)
    for tier, cap in ipairs(TIER_CAPS) do
        if attitude <= cap then return tier - 1 end
    end
    return 3
end


--- Logs every god's favour, so the log says *who* is worth praying to.
local function report_favour()
    local faction = cm:get_faction(cm:get_local_faction())
    if not faction then return end
    local parts = {}
    for _, god in ipairs(GODS) do
        local key = "troy_god_attitude_" .. god
        if faction:has_pooled_resource(key) then
            local value = faction:pooled_resource(key):value()
            parts[#parts + 1] = string.format("%s=%d(t%d)", god, value, tier_of(value))
        end
    end
    log("favour: " .. table.concat(parts, " "))
end


--- Pulses the action button so the player can see which one is waiting.
local function pulse(action, on)
    local button = action_button(action)
    if button then
        pulse_uicomponent(button, on, 2)
    end
end


local function turns_since_hecatomb()
    local last = cm:get_saved_value(SAVED_LAST_HECATOMB)
    if not last then return nil end
    return cm:turn_number() - last
end


--- The actual check. `at_end_turn` makes it pulse rather than only log.
local function check(at_end_turn)
    local pending = {}
    for action, meta in pairs(ACTIONS) do
        local available = is_available(action)
        if available == true then
            pending[#pending + 1] = meta.label
            if at_end_turn then pulse(action, true) end
        elseif available == false and at_end_turn then
            pulse(action, false)
        end
    end

    if #pending > 0 then
        log("可以舉辦但尚未舉辦：" .. table.concat(pending, "、"))
        report_favour()
        return true
    end

    -- Panel closed: fall back to "how long since the last hecatomb".
    local since = turns_since_hecatomb()
    if since and since >= REMIND_AFTER_TURNS then
        log(string.format("已 %d 回合未舉行百牲祭（神祇面板未開啟，無法確認是否負擔得起）", since))
        report_favour()
        return true
    end
    return false
end


function hecatomb_reminder()
    log("loaded")

    core:add_listener(
        "hecatomb_reminder_turn_start",
        "FactionTurnStart",
        function(context) return context:faction():name() == cm:get_local_faction() end,
        function() check(false) end,
        true
    )

    -- Fires the moment the end-turn button is pressed, which is when the
    -- game's own end-turn warnings appear. vanilla never listens to this
    -- event, so there is nothing to collide with.
    core:add_listener(
        "hecatomb_reminder_end_turn",
        "FactionAboutToEndTurn",
        function(context) return context:faction():name() == cm:get_local_faction() end,
        function() check(true) end,
        true
    )

    core:add_listener(
        "hecatomb_reminder_performed",
        "FactionInitiatesHecatomb",
        function(context) return context:faction():name() == cm:get_local_faction() end,
        function()
            cm:set_saved_value(SAVED_LAST_HECATOMB, cm:turn_number())
            pulse("hecatomb", false)
            log("百牲祭已舉行，計時重置")
        end,
        true
    )
end
