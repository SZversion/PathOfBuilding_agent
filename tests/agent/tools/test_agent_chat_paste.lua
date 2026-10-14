-- Ctrl+V can be released, and its clipboard restored, before the next UI frame.
local previousNewClass = newClass
local previousJson = package.loaded.dkjson
newClass = function(...) return { } end
package.loaded.dkjson = { }
local class = dofile("src/Classes/AgentChatPane.lua")
local input = { buf = "", caret = 1 }
function input:Insert(text) self.buf = self.buf .. text end
function input:ReplaceSel(text) self.buf = text; self.sel = nil end
local pane = { isOverlay = true, controls = { input = input }, selControl = input }
function pane:ProcessControlsInput() end
main = { mode = "BUILD", modes = { BUILD = { agentChatPane = pane } }, inputEvents = { } }
t_insert = table.insert
local file = assert(io.open("src/Modules/Main.lua", "r"))
local source = file:read("*a"):gsub("\r", "")
file:close()
local body = assert(source:match("function main:OnKeyDown%(key, doubleClick%)\n(.-)\nend"))
assert(loadstring("function main:OnKeyDown(key, doubleClick)\n" .. body .. "\nend"))()
local ctrl, clipboard = true, ""
IsKeyDown = function(key) return key == "CTRL" and ctrl end
Paste = function() return clipboard end
for _, text in ipairs({ "QA", "arc 스킬은 시전속도가 얼마야?" }) do
	input.buf, input.sel = "", nil
	main.inputEvents = { }
	ctrl, clipboard = true, text
	main:OnKeyDown("v", false)
	ctrl, clipboard = false, ""
	class.HandleInputEvent(pane, main.inputEvents[1], 0, 0)
	assert(input.buf == text, "queued Ctrl+V lost its clipboard text")
end
input.buf, input.sel, input.caret = "old", 1, 4
main.inputEvents = { }
ctrl, clipboard = true, "replacement"
main:OnKeyDown("v", false)
ctrl, clipboard = false, ""
class.HandleInputEvent(pane, main.inputEvents[1], 0, 0)
assert(input.buf == "replacement", "paste must replace the selection")
pane.selControl = nil
main.inputEvents = { }
ctrl, clipboard = true, "unrelated"
main:OnKeyDown("v", false)
assert(main.inputEvents[1].pasteText == nil, "do not capture clipboard outside focused Agent input")
newClass, package.loaded.dkjson = previousNewClass, previousJson
print("Agent queued paste, UTF-8, selection, and focus checks passed")
