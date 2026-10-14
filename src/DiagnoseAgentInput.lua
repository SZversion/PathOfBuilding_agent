#@ SimpleGraphic
-- Temporary input-path diagnostics; launch normally with Launch.lua after diagnosis.
dofile("Launch.lua")
local tracePath = assert(os.getenv("POB_AGENT_INPUT_TRACE"), "POB_AGENT_INPUT_TRACE is required")
local function trace(text)
	local file = assert(io.open(tracePath, "a"))
	file:write(tostring(GetTime()), " ", text, "\n")
	file:close()
end
local onChar = launch.OnChar
function launch:OnChar(key)
	trace("CHAR bytes=" .. tostring(#key))
	return onChar(self, key)
end
local onKeyDown = launch.OnKeyDown
function launch:OnKeyDown(key, doubleClick)
	trace("KEY " .. tostring(key) .. " ctrl=" .. tostring(IsKeyDown("CTRL")))
	return onKeyDown(self, key, doubleClick)
end
local onFrame = launch.OnFrame
function launch:OnFrame()
	local events = self.main and self.main.inputEvents
	if events and next(events) then
		local list = { }
		for index, event in pairs(events) do
			list[#list + 1] = tostring(index) .. ":" .. tostring(event.type)
		end
		trace("FRAME " .. table.concat(list, ","))
	end
	local result = onFrame(self)
	if events and next(events) then trace("UNCONSUMED") end
	local build = self.main and self.main.modes and self.main.modes.BUILD
	local pane = build and build.agentChatPane
	if pane and pane.isOverlay then
		local state = tostring(pane.selControl == pane.controls.input) .. ":" .. tostring(#pane.controls.input.buf)
		if state ~= self.lastInputTraceState then
			trace("INPUT focused:bytes=" .. state)
			self.lastInputTraceState = state
		end
	end
	return result
end
