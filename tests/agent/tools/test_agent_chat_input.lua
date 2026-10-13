local previousNewClass = newClass
local previousWidth = DrawStringWidth
local previousJson = package.loaded.dkjson
newClass = function(...)
	return { constructor = select(select("#", ...), ...) }
end
package.loaded.dkjson = { }
DrawStringWidth = function(_, _, text)
	local count = 0
	for _ in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do count = count + 1 end
	return count * 10
end
local class = dofile("src/Classes/AgentChatPane.lua")
local function upvalue(fn, wanted)
	for index = 1, 30 do
		local name, value = debug.getupvalue(fn, index)
		if name == wanted then return value end
	end
	error("missing upvalue: " .. wanted)
end
local layout = upvalue(class.DrawOverlay, "inputLayout")
local configure = upvalue(class.constructor, "configureChatInput")
local withLayout = upvalue(configure, "withInputLayout")
local input = { buf = "", caret = 1, font = "VAR", width = 100, height = 20 }
input.GetSize = function(self) return self.width, self.height end
assert(layout(input).lines == 1)
input.buf = string.rep("a", 40)
assert(layout(input).lines == 5)
assert(layout(input).text:gsub("\n", "") == input.buf)
input.buf = input.buf .. "a"
assert(layout(input).lines == 6)
input.width = 180
assert(layout(input).lines == 3)
input.buf = "가나다라마바사아자"
input.width = 100
local wrapped = layout(input)
assert(wrapped.lines == 2 and wrapped.text == "가나다라마바사아\n자")
input.caret = 25
withLayout(input, function(self)
	assert(self.caret == 26)
	self.caret = 25
end)
assert(input.buf == "가나다라마바사아자" and input.caret == 25)
local ok = pcall(withLayout, input, function() error("draw failure") end)
assert(not ok and input.buf == "가나다라마바사아자" and input.displayLayout == nil)
input.buf = "a\nb\nc\nd\ne\nf"
assert(layout(input).lines == 6)
input.controls = { scrollBarH = { }, scrollBarV = { } }
local function dimensions(self, content, view)
	self.enabled = content > view
	self.offset = 0
end
input.controls.scrollBarH.SetContentDimension = dimensions
input.controls.scrollBarV.SetContentDimension = dimensions
input.Draw = function() end
input.ScrollCaretIntoView = function() end
input.OnKeyDown = function() end
configure(input)
input.height = 76
input:UpdateScrollBars()
assert(input.controls.scrollBarV.shown() and input.controls.scrollBarV.width == 6)
assert(input.controls.scrollBarH.shown == false and not input.controls.scrollBarH.enabled)
input.buf = "a\nb\nc\nd\ne"
input:UpdateScrollBars()
assert(not input.controls.scrollBarV.shown())
input.buf = ""
input:UpdateScrollBars()
assert(not input.controls.scrollBarV.enabled)
newClass, DrawStringWidth, package.loaded.dkjson = previousNewClass, previousWidth, previousJson
print("agent chat wrapping, UTF-8 mapping, and scrollbar checks passed")
