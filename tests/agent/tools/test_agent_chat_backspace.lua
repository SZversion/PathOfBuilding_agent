local previousNewClass = newClass
local previousJson = package.loaded.dkjson
local previousCpath = package.cpath
package.cpath = "runtime/?.dll;" .. package.cpath
local classes = { }
newClass = function(name, ...)
	local class = { constructor = select(select("#", ...), ...) }
	classes[name] = class
	return class
end
package.loaded.dkjson = { }
dofile("src/Classes/EditControl.lua")
local edit = assert(classes.EditControl)
local chat = dofile("src/Classes/AgentChatPane.lua")
local configure
for index = 1, 30 do
	local name, value = debug.getupvalue(chat.constructor, index)
	if name == "configureChatInput" then configure = value; break end
end
assert(configure)
GetTime = function() return 0 end
IsKeyDown = function() return false end
DrawStringWidth = function(_, _, text) return #text end
local input = { caret = 1, font = "VAR", width = 240, height = 20, filterPattern = "[^%C\t\n]" }
input.Object = input
input.GetSize = function(self) return self.width, self.height end
input.IsShown = function() return true end
input.IsEnabled = function() return true end
input.GetMouseOverControl = function() end
input.ScrollCaretIntoView = function() end
input.AddUndoState = function() end
input.ReplaceSel = edit.ReplaceSel
input.OnKeyDown = edit.OnKeyDown
input.Draw = function() end
input.controls = { scrollBarH = { }, scrollBarV = { } }
input.controls.scrollBarH.SetContentDimension = function() end
input.controls.scrollBarV.SetContentDimension = function() end
configure(input)
for _, case in ipairs({
	{ "가나다", "가나" },
	{ "가", "" },
	{ "A가", "A" },
	{ "가A", "가" },
	{ "A🙂", "A" },
	{ "", "" },
}) do
	input.buf, input.caret, input.sel = case[1], #case[1] + 1, nil
	input:OnKeyDown("BACK")
	assert(input.buf == case[2], "Backspace must delete one UTF-8 character")
	assert(input.caret == #case[2] + 1)
end
input.buf, input.caret, input.sel = "가나다", 7, 4
input:OnKeyDown("BACK")
assert(input.buf == "가다", "preserve selection deletion")
input.buf, input.caret, input.sel = "가나", 1, nil
input:OnKeyDown("BACK")
assert(input.buf == "가나" and input.caret == 1)
newClass, package.loaded.dkjson = previousNewClass, previousJson
package.cpath = previousCpath
print("Agent UTF-8 Backspace and selection checks passed")
