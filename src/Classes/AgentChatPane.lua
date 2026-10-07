-- Path of Building
--
-- Class: Agent Chat Pane
-- Local-only chat UI overlay for the build screen.
--
local t_insert = table.insert
local t_remove = table.remove
local m_max = math.max
local m_min = math.min
local dkjson = require "dkjson"

local DEFAULT_WIDTH = 320
local DEFAULT_HEIGHT = 240
local MIN_WIDTH = 200
local MIN_HEIGHT = 150
local HEADER_HEIGHT = 24
local INPUT_HEIGHT = 20
local SEND_HEIGHT = 20
local INPUT_FONT_SIZE = 14
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
		{ role = "Agent", text = "PoB Agent에 연결되었습니다. 현재 빌드에 대해 질문해 보세요." },
	}
	self.requestPending = false
	self.scrollToBottom = true
	self.resizing = false
	self.resizeCursorHidden = false

	self.controls.close = new("ButtonControl", {"TOPRIGHT", self, "TOPRIGHT"}, {-4, 3, 16, 16}, "x", function()
		self:ToggleOverlay(false)
	end)
	self.controls.input = new("EditControl", {"BOTTOMLEFT", self, "BOTTOMLEFT"}, {8, -8, 0, INPUT_HEIGHT}, "", nil, "^%C\t\n", 1000, nil, INPUT_FONT_SIZE, true)
	self.controls.input.placeholder = "Type a message..."
	self.controls.input.textYOffset = math.floor((INPUT_HEIGHT - 4 - INPUT_FONT_SIZE) / 2)
	self.controls.input.width = function()
		local width = self:GetSize()
		local sendWidth = self.controls.send and self.controls.send:GetSize() or 48
		return m_max(24, width - sendWidth - 24)
	end
	self.controls.send = new("ButtonControl", {"BOTTOMRIGHT", self, "BOTTOMRIGHT"}, {-8, -8, 48, SEND_HEIGHT}, "Send", function()
		self:SendMessage()
	end)
	self.controls.send.overSizeText = (INPUT_FONT_SIZE - (SEND_HEIGHT - 4)) / 2
	self.controls.send.width = function()
		local width = self:GetSize()
		return m_max(32, m_min(48, width - 70))
	end
	self.controls.send.x = -8
	self.controls.historyScroll = new("ScrollBarControl", {"TOPRIGHT", self, "TOPRIGHT"}, {-3, HEADER_HEIGHT + 6, 14, 0}, MESSAGE_LINE_HEIGHT * 3, "VERTICAL", true)
	self.controls.historyScroll.height = function()
		local _, height = self:GetSize()
		return m_max(0, height - HEADER_HEIGHT - SEND_HEIGHT - 28)
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
	self:SetResizeCursorHidden(false)
	if open then
		self:RaiseOverlay()
		self:SelectControl(self.controls.input)
		self.scrollToBottom = true
	else
		self:SelectControl()
	end
end

function AgentChatPaneClass:SetResizeCursorHidden(hidden)
	if self.resizeCursorHidden == hidden then
		return
	end
	ShowCursor(not hidden)
	self.resizeCursorHidden = hidden
end

function AgentChatPaneClass:RaiseOverlay()
	local panes = self.build and self.build.overlayPanes
	if not panes then
		return
	end
	for index, pane in ipairs(panes) do
		if pane == self then
			t_remove(panes, index)
			t_insert(panes, self)
			return
		end
	end
end

function AgentChatPaneClass:ReleaseFocus()
	self:SelectControl()
end

function AgentChatPaneClass:SendMessage()
	if self.requestPending then
		return
	end
	local message = (self.controls.input.buf or ""):match("^%s*(.-)%s*$")
	if message == "" then
		return
	end
	local build = self.build
	local buildPath = build and build.dbFileName
	local buildRoot = main and main.buildPath
	local normalizedPath = type(buildPath) == "string" and buildPath:gsub("\\", "/")
	local normalizedRoot = type(buildRoot) == "string" and buildRoot:gsub("\\", "/")
	if not normalizedPath or not normalizedRoot or normalizedPath:sub(1, #normalizedRoot):lower() ~= normalizedRoot:lower() then
		t_insert(self.messages, { role = "Agent", text = "먼저 현재 빌드를 PoB의 Builds 폴더에 저장한 뒤 다시 질문해 주세요." })
		self.scrollToBottom = true
		return
	end
	local buildFile = normalizedPath:sub(#normalizedRoot + 1)
	if buildFile == "" then
		t_insert(self.messages, { role = "Agent", text = "저장된 현재 빌드 파일을 찾을 수 없습니다. 빌드를 저장한 뒤 다시 질문해 주세요." })
		self.scrollToBottom = true
		return
	end
	local configPath = GetScriptPath():gsub("[\\/]+$", "") .. "/AgentChatConfig.json"
	local configFile = io.open(configPath, "r")
	local config = configFile and dkjson.decode(configFile:read("*a"))
	if configFile then configFile:close() end
	if type(config) ~= "table" or type(config.url) ~= "string" or type(config.token) ~= "string" then
		t_insert(self.messages, { role = "Agent", text = "에이전트 접속 설정을 읽지 못했습니다. 설치 폴더의 AgentChatConfig.json을 확인해 주세요." })
		self.scrollToBottom = true
		return
	end
	t_insert(self.messages, { role = "You", text = message })
	t_insert(self.messages, { role = "Agent", text = "답변을 기다리는 중..." })
	local responseIndex = #self.messages
	while #self.messages > 40 do
		t_remove(self.messages, 1)
		responseIndex = responseIndex - 1
	end
	self.requestPending = true
	self.controls.input:SetText("", true)
	self.scrollToBottom = true
	self:SelectControl(self.controls.input)
	local requestBody = dkjson.encode({ build_file = buildFile, question = message })
	local requestHeaders = "Authorization: Bearer " .. config.token .. "\r\nContent-Type: application/json\r\nAccept: application/json"
	local scriptId = LaunchSubScript([[
		local url, requestHeadersText, requestBody = ...
		local curl = require("lcurl.safe")
		local responseBody = ""
		local responseTooLarge = false
		local requestHeaders = { }
		for header in requestHeadersText:gmatch("[^\r\n]+") do
			table.insert(requestHeaders, header)
		end
		local easy = curl.easy()
		easy:setopt_url(url)
		easy:setopt(curl.OPT_HTTPHEADER, requestHeaders)
		easy:setopt(curl.OPT_POST, true)
		easy:setopt(curl.OPT_POSTFIELDS, requestBody)
		easy:setopt(curl.OPT_CONNECTTIMEOUT, 10)
		easy:setopt(curl.OPT_TIMEOUT, 310)
		easy:setopt_writefunction(function(data)
			if #responseBody + #data > 1048576 then
				responseTooLarge = true
				return false
			end
			responseBody = responseBody .. data
			return true
		end)
		local _, requestError = easy:perform()
		local status = easy:getinfo(curl.INFO_RESPONSE_CODE)
		easy:close()
		if responseTooLarge then
			return "", status, "Agent response exceeded 1 MB"
		end
		if requestError then
			return "", status, requestError:msg()
		end
		return responseBody, status, ""
	]], "", "", config.url, requestHeaders, requestBody)
	if not scriptId then
		self.requestPending = false
		self.messages[responseIndex] = { role = "Agent", text = "에이전트 요청을 시작하지 못했습니다." }
		return
	end
	launch:RegisterSubScript(scriptId, function(responseBody, status, requestError)
		self.requestPending = false
		local reply
		if requestError and requestError ~= "" then
			reply = "에이전트 연결 오류: " .. requestError
		elseif status ~= 200 then
			local errorBody = responseBody ~= "" and dkjson.decode(responseBody)
			reply = type(errorBody) == "table" and (errorBody.detail or errorBody.error) or ("에이전트 서버 응답 오류 (HTTP " .. tostring(status) .. ")")
		else
			local result = dkjson.decode(responseBody)
			if type(result) == "table" and type(result.answer) == "string" and result.answer ~= "" then
				reply = result.answer
			elseif type(result) == "table" and type(result.error) == "table" then
				reply = result.error.message or result.error.code or "요청을 처리하지 못했습니다."
			else
				reply = "에이전트 응답을 해석하지 못했습니다."
			end
		end
		self.messages[responseIndex] = { role = "Agent", text = tostring(reply) }
		while #self.messages > 40 do
			t_remove(self.messages, 1)
			responseIndex = responseIndex - 1
		end
		self.scrollToBottom = true
	end)
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
	local conversationBottom = y + height - SEND_HEIGHT - 18
	return cursorX >= x + 4 and cursorX < x + width - 18
		and cursorY >= conversationTop and cursorY < conversationBottom
end

function AgentChatPaneClass:IsMouseOverResizeGrip(cursorX, cursorY)
	if not self.isOverlay then
		return false
	end
	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	return cursorX >= x + width - 14 and cursorY >= y + height - 14
		and cursorX < x + width and cursorY < y + height
end

function AgentChatPaneClass:HandleOverlayClick(key, cursorX, cursorY)
	if key ~= "LEFTBUTTON" or not self.isOverlay then
		return false
	end
	self:RaiseOverlay()
	local x, y = self.overlayX, self.overlayY
	local width, height = self:GetSize()
	if self:IsMouseOverResizeGrip(cursorX, cursorY) then
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
		local nextSelected = selected:OnKeyUp(key)
		if selected == self.controls.send then
			nextSelected = nextSelected or self.controls.input
		end
		self:SelectControl(nextSelected)
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
		elseif self.controls.input:IsMouseInBounds() then
			self:SelectControl(self.controls.input:OnKeyUp(event.key))
		end
		return self:IsMouseInOverlay(cursorX, cursorY)
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
		local blockY = block.y - scroll.offset
		local userMessage = block.role == "You"
		SetDrawColor(userMessage and 0.12 or 0.18, userMessage and 0.16 or 0.18, userMessage and 0.22 or 0.18)
		DrawImage(nil, 2, blockY, width - 4, block.height)
		SetDrawColor(0.72, 0.72, 0.72)
		DrawString(7, blockY + 3, "LEFT", MESSAGE_FONT_SIZE, "VAR BOLD", block.role)
		SetDrawColor(1, 1, 1)
		for lineIndex, line in ipairs(block.lines) do
			DrawString(7, blockY + 18 + (lineIndex - 1) * MESSAGE_LINE_HEIGHT, "LEFT", MESSAGE_FONT_SIZE, "VAR", line)
		end
	end
	SetViewport()
end

function AgentChatPaneClass:DrawOverlay(viewPort)
	if not self.isOverlay then
		self:SetResizeCursorHidden(false)
		return
	end
	local cursorX, cursorY = GetCursorPos()
	local resizeCursor = self.resizing or self:IsMouseOverResizeGrip(cursorX, cursorY)
	self:SetResizeCursorHidden(resizeCursor)
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
	DrawString(x + 8, y + 5, "LEFT", 14, "VAR BOLD", self.requestPending and "PoB Agent — 답변 중" or "PoB Agent")
	SetDrawColor(0.5, 0.5, 0.5)
	DrawImage(nil, x + 3, y + HEADER_HEIGHT, width - 6, 1)

	local conversationX = x + 4
	local conversationY = y + HEADER_HEIGHT + 6
	local conversationWidth = width - 22
	local conversationHeight = m_max(1, height - HEADER_HEIGHT - SEND_HEIGHT - 22)
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
	if resizeCursor then
		local function drawCursorLine(x1, y1, x2, y2, lineWidth)
			local dx, dy = x2 - x1, y2 - y1
			local length = math.sqrt(dx * dx + dy * dy)
			local ox, oy = -dy / length * lineWidth / 2, dx / length * lineWidth / 2
			DrawImageQuad(nil, x1 + ox, y1 + oy, x2 + ox, y2 + oy, x2 - ox, y2 - oy, x1 - ox, y1 - oy)
		end
		local cx, cy = cursorX - 7, cursorY - 7
		SetDrawLayer(13)
		SetDrawColor(0, 0, 0)
		drawCursorLine(cx + 1, cy + 1, cx + 6, cy + 1, 4)
		drawCursorLine(cx + 1, cy + 1, cx + 1, cy + 6, 4)
		drawCursorLine(cx + 9, cy + 9, cx + 14, cy + 9, 4)
		drawCursorLine(cx + 9, cy + 9, cx + 9, cy + 14, 4)
		drawCursorLine(cx + 3, cy + 3, cx + 12, cy + 12, 5)
		SetDrawColor(1, 1, 1)
		drawCursorLine(cx + 1, cy + 1, cx + 6, cy + 1, 2)
		drawCursorLine(cx + 1, cy + 1, cx + 1, cy + 6, 2)
		drawCursorLine(cx + 9, cy + 9, cx + 14, cy + 9, 2)
		drawCursorLine(cx + 9, cy + 9, cx + 9, cy + 14, 2)
		drawCursorLine(cx + 3, cy + 3, cx + 12, cy + 12, 2)
	end
	SetDrawLayer(0)
end

return AgentChatPaneClass
