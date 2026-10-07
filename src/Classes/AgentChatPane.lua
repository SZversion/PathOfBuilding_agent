-- Path of Building
--
-- Class: Agent Chat Pane
-- Local-only chat UI overlay for the build screen.
--
local t_insert = table.insert
local t_remove = table.remove
local m_max = math.max
local m_min = math.min

local DEFAULT_WIDTH = 240
local DEFAULT_HEIGHT = 180
local MIN_WIDTH = 200
local MIN_HEIGHT = 150
local HEADER_HEIGHT = 24
local INPUT_HEIGHT = 34
local MESSAGE_FONT_SIZE = 14
local MESSAGE_LINE_HEIGHT = 16

local function wrapText(text, width)
	local lines = { }
	for paragraph in (tostring(text) .. "\n"):gmatch("(.-)\n") do
		local line = ""
		for word in paragraph:gmatch("%S+%s*") do
			local candidate = line .. word
			if line ~= "" and DrawStringWidth(MESSAGE_FONT_SIZE, "VAR", candidate) > width then
				lines[#lines + 1] = line:gsub("%s+$", "")
				line = word:gsub("^%s+", "")
			else
				line = candidate
			end
		end
		lines[#lines + 1] = line:gsub("%s+$", "")
	end
	return lines
end

local AgentChatPaneClass = newClass("AgentChatPane", "Control", "ControlHost", function(self, build)
	self.Control(nil, {0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT})
	self.ControlHost()
	self.build = build
	self.isOverlay = false
	self.overlayX = 320
	self.overlayY = 50
	self.x = self.overlayX
	self.y = self.overlayY
	self.messages = {
		{ role = "Preview", text = "This chat is a UI preview. Agent replies are not connected yet." },
	}
	self.scrollToBottom = true
	self.resizing = false

	self.controls.close = new("ButtonControl", {"TOPRIGHT", self, "TOPRIGHT"}, {-4, 3, 16, 16}, "x", function()
		self:ToggleOverlay(false)
	end)
	self.controls.input = new("EditControl", {"BOTTOMLEFT", self, "BOTTOMLEFT"}, {8, -8, 0, INPUT_HEIGHT}, "", "Type a message...", "^%C\t\n", 1000, nil, 14, true)
	self.controls.input.width = function()
		local width = self:GetSize()
		local sendWidth = self.controls.send and self.controls.send:GetSize() or 54
		return m_max(24, width - sendWidth - 34)
	end
	self.controls.send = new("ButtonControl", {"BOTTOMRIGHT", self, "BOTTOMRIGHT"}, {-8, -8, 54, INPUT_HEIGHT}, "Send", function()
		self:SendMessage()
	end)
	self.controls.send.width = function()
		local width = self:GetSize()
		return m_max(32, m_min(54, width - 70))
	end
	self.controls.send.x = -18
	self.controls.historyScroll = new("ScrollBarControl", {"TOPRIGHT", self, "TOPRIGHT"}, {-3, HEADER_HEIGHT + 6, 14, 0}, MESSAGE_LINE_HEIGHT * 3, "VERTICAL", true)
	self.controls.historyScroll.height = function()
		local _, height = self:GetSize()
		return m_max(0, height - HEADER_HEIGHT - INPUT_HEIGHT - 28)
	end
end)

function AgentChatPaneClass:ToggleOverlay(open)
	if open == nil then
		open = not self.isOverlay
	end
	if self.isOverlay == open then
		return
	end
	self.isOverlay = open
	self.resizing = false
	if open then
		self:SelectControl(self.controls.input)
		self.scrollToBottom = true
	else
		self:SelectControl()
	end
end

function AgentChatPaneClass:ReleaseFocus()
	self:SelectControl()
end

function AgentChatPaneClass:SendMessage()
	local message = (self.controls.input.buf or ""):match("^%s*(.-)%s*$")
	if message == "" then
		return
	end
	t_insert(self.messages, { role = "You", text = message })
	while #self.messages > 40 do
		t_remove(self.messages, 1)
	end
	self.controls.input:SetText("", true)
	self.scrollToBottom = true
	self:SelectControl(self.controls.input)
end

function AgentChatPaneClass:IsMouseInOverlay(cursorX, cursorY)
	if not self.isOverlay then
		return false
	end
	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	return cursorX >= x and cursorY >= y and cursorX < x + width and cursorY < y + height
end

function AgentChatPaneClass:IsMouseInConversation(cursorX, cursorY)
	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	local conversationTop = y + HEADER_HEIGHT + 6
	local conversationBottom = y + height - INPUT_HEIGHT - 18
	return cursorX >= x + 4 and cursorX < x + width - 18
		and cursorY >= conversationTop and cursorY < conversationBottom
end

function AgentChatPaneClass:HandleOverlayClick(key, cursorX, cursorY)
	if key ~= "LEFTBUTTON" or not self.isOverlay then
		return false
	end
	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	if cursorX >= x + width - 14 and cursorY >= y + height - 14 then
		self.resizing = true
		self.resizeStartX = cursorX
		self.resizeStartY = cursorY
		self.resizeStartWidth = width
		self.resizeStartHeight = height
		return true
	end
	local control = self:GetMouseOverControl()
	if control and control.OnKeyDown then
		self:SelectControl(control:OnKeyDown(key))
	else
		self:SelectControl()
	end
	return true
end

function AgentChatPaneClass:HandleOverlayRelease(key)
	if not self.isOverlay then
		return false
	end
	if key == "LEFTBUTTON" and self.resizing then
		self.resizing = false
		return true
	end
	local selected = self.selControl
	if selected and selected.OnKeyUp then
		self:SelectControl(selected:OnKeyUp(key))
		return true
	end
	return false
end

function AgentChatPaneClass:HandleInputEvent(event, cursorX, cursorY)
	if not self.isOverlay then
		return false
	end
	if event.type == "KeyUp" and (event.key == "WHEELDOWN" or event.key == "WHEELUP") then
		if self:IsMouseInConversation(cursorX, cursorY) then
			self.controls.historyScroll:Scroll(event.key == "WHEELDOWN" and 1 or -1)
			return true
		end
		return false
	end
	if not self.selControl then
		return false
	end
	self:ProcessControlsInput({event}, main.viewPort)
	return true
end

function AgentChatPaneClass:BuildMessageBlocks(textWidth)
	local blocks = { }
	local totalHeight = 0
	for _, message in ipairs(self.messages) do
		local lines = wrapText(message.text, textWidth - 12)
		local height = 18 + #lines * MESSAGE_LINE_HEIGHT + 6
		blocks[#blocks + 1] = {
			role = message.role,
			lines = lines,
			y = totalHeight,
			height = height,
		}
		totalHeight = totalHeight + height + 5
	end
	return blocks, totalHeight
end

function AgentChatPaneClass:DrawConversation(x, y, width, height)
	local innerWidth = m_max(20, width - 28)
	local blocks, contentHeight = self:BuildMessageBlocks(innerWidth)
	local scroll = self.controls.historyScroll
	scroll:SetContentDimension(contentHeight, height)
	if self.scrollToBottom then
		scroll:SetOffset(scroll.offsetMax or 0)
		self.scrollToBottom = false
	end

	SetViewport(x, y, width, height)
	for _, block in ipairs(blocks) do
		local blockY = y + block.y - scroll.offset
		local userMessage = block.role == "You"
		SetDrawColor(userMessage and 0.12 or 0.18, userMessage and 0.16 or 0.18, userMessage and 0.22 or 0.18)
		DrawImage(nil, x + 2, blockY, width - 4, block.height)
		SetDrawColor(0.72, 0.72, 0.72)
		DrawString(x + 7, blockY + 3, "LEFT", MESSAGE_FONT_SIZE, "VAR BOLD", block.role)
		SetDrawColor(1, 1, 1)
		for lineIndex, line in ipairs(block.lines) do
			DrawString(x + 7, blockY + 18 + (lineIndex - 1) * MESSAGE_LINE_HEIGHT, "LEFT", MESSAGE_FONT_SIZE, "VAR", line)
		end
	end
	SetViewport()
end

function AgentChatPaneClass:DrawOverlay(viewPort)
	if not self.isOverlay then
		return
	end
	local cursorX, cursorY = GetCursorPos()
	local minWidth = m_min(MIN_WIDTH, viewPort.width)
	local minHeight = m_min(MIN_HEIGHT, viewPort.height)
	local maxWidth = m_max(minWidth, viewPort.width)
	local maxHeight = m_max(minHeight, viewPort.height)

	if self.resizing then
		self.width = m_max(minWidth, m_min(maxWidth, self.resizeStartWidth + cursorX - self.resizeStartX))
		self.height = m_max(minHeight, m_min(maxHeight, self.resizeStartHeight + cursorY - self.resizeStartY))
	end
	self.width = m_min(self.width, maxWidth)
	self.height = m_min(self.height, maxHeight)
	self.x = self.overlayX
	self.y = self.overlayY
	self.overlayX = m_max(viewPort.x, m_min(self.overlayX, viewPort.x + viewPort.width - self.width))
	self.overlayY = m_max(viewPort.y, m_min(self.overlayY, viewPort.y + viewPort.height - self.height))
	self.x = self.overlayX
	self.y = self.overlayY
	self.width = m_max(minWidth, self.width)
	self.height = m_max(minHeight, self.height)

	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	SetDrawLayer(12)
	SetDrawColor(0.08, 0.08, 0.08, 0.97)
	DrawImage(nil, x, y, width, height)
	SetDrawColor(0.5, 0.5, 0.5)
	DrawImage(nil, x, y, width, 1)
	DrawImage(nil, x, y + height - 1, width, 1)
	DrawImage(nil, x, y, 1, height)
	DrawImage(nil, x + width - 1, y, 1, height)
	SetDrawColor(0.18, 0.18, 0.18)
	DrawImage(nil, x + 1, y + 1, width - 2, HEADER_HEIGHT - 1)
	SetDrawColor(0.85, 0.85, 0.85)
	DrawString(x + 8, y + 5, "LEFT", 14, "VAR BOLD", "PoB Agent — preview")
	SetDrawColor(0.5, 0.5, 0.5)
	DrawImage(nil, x + 3, y + HEADER_HEIGHT, width - 6, 1)

	local conversationX = x + 4
	local conversationY = y + HEADER_HEIGHT + 6
	local conversationWidth = width - 22
	local conversationHeight = m_max(1, height - HEADER_HEIGHT - INPUT_HEIGHT - 22)
	SetDrawColor(0.03, 0.03, 0.03)
	DrawImage(nil, conversationX, conversationY, conversationWidth, conversationHeight)
	self:DrawConversation(conversationX, conversationY, conversationWidth, conversationHeight)

	self.controls.input.x = 8
	self.controls.input.y = -8
	self.controls.input.height = INPUT_HEIGHT
	self.controls.send.y = -8
	self.controls.historyScroll.y = HEADER_HEIGHT + 6
	self.controls.historyScroll.height = conversationHeight
	self:DrawControls(viewPort)

	SetDrawColor(0.6, 0.6, 0.6)
	for index = 0, 2 do
		DrawImage(nil, x + width - 5 - index * 3, y + height - 2, 2, 1)
		DrawImage(nil, x + width - 2, y + height - 5 - index * 3, 1, 2)
	end
	SetDrawLayer(0)
end

return AgentChatPaneClass
