-- Local, allowlisted control channel for the running PoB process.
-- Requests are handled from main:OnFrame so all PoB access stays on the UI thread.
local socket = require("socket")
local json = require("dkjson")
local errors = LoadModule("Modules/AgentErrorRegistry")

local MAX_REQUEST_BYTES = 64 * 1024
local MAX_RESPONSE_BYTES = 1024 * 1024
local CLIENT_TIMEOUT_SECONDS = 5
local PROTOCOL_VERSION = 1

local function errorResponse(code, stage, message)
	return { ok = false, error = {
		code = code, error_ref = errors.parent(code), recovery_class = "REJECT",
		stage = stage, retryable = false, attempt = 1, max_attempts = 1,
		message = message, details = {}, next_action = "reject_request",
		secondary_causes = {}, side_effect = "none", snapshotRevision = nil,
	} }
end

local function makeTokenAndPid()
	local ok, ffi = pcall(require, "ffi")
	if not ok then return nil, nil, "LuaJIT FFI is unavailable" end
	local cdefOk, cdefErr = pcall(ffi.cdef, [[
		typedef long pob_agent_ntstatus;
		typedef unsigned char pob_agent_byte;
		pob_agent_ntstatus BCryptGenRandom(void *algorithm, pob_agent_byte *buffer, unsigned long length, unsigned long flags);
		unsigned long GetCurrentProcessId(void);
	]])
	if not cdefOk then
		local alreadyDefined = pcall(ffi.typeof, "pob_agent_byte")
		if not alreadyDefined then return nil, nil, tostring(cdefErr) end
	end
	local cryptoOk, crypto = pcall(ffi.load, "bcrypt")
	local kernelOk, kernel = pcall(ffi.load, "kernel32")
	if not cryptoOk or not kernelOk then return nil, nil, "Windows random provider is unavailable" end
	local bytes = ffi.new("pob_agent_byte[32]")
	local randomOk, status = pcall(function()
		return crypto.BCryptGenRandom(nil, bytes, 32, 2)
	end)
	if not randomOk or tonumber(status) < 0 then return nil, nil, "Windows random provider failed" end
	local parts = {}
	for index = 0, 31 do parts[#parts + 1] = string.format("%02x", tonumber(bytes[index])) end
	local pidOk, pid = pcall(function() return tonumber(kernel.GetCurrentProcessId()) end)
	if not pidOk or not pid then return nil, nil, "Unable to identify PoB process" end
	return table.concat(parts), pid
end

local function encode(value)
	local ok, result = pcall(json.encode, value)
	if not ok or type(result) ~= "string" then return nil end
	return result
end

local function scanBuilds()
	local helpers = LoadModule("Modules/BuildListHelpers")
	local result = {}
	local function scan(subPath)
		local entries = helpers.ScanFolder(subPath)
		for _, entry in ipairs(entries or {}) do
			if entry.folderName and entry.folderName:sub(1, 1) ~= "." then
				scan((entry.subPath or subPath) .. entry.folderName .. "/")
			elseif entry.fullFileName and entry.buildName and not entry.folderName then
				result[#result + 1] = {
					id = entry.fullFileName,
					name = entry.buildName,
					level = entry.level,
					className = entry.className,
					ascendClassName = entry.ascendClassName,
				}
			end
		end
	end
	scan("")
	return result
end

local function findBuild(id)
	if type(id) ~= "string" or id == "" or #id > 4096 then return nil end
	for _, entry in ipairs(scanBuilds()) do
		if entry.id == id then return entry end
	end
	return nil
end

local function currentBuild(main)
	local adapter = LoadModule("Modules/AgentInProcess")
	local build, err = adapter.currentBuild(main)
	if not build then return nil, err or "running PoB build is unavailable" end
	return build
end

local function dispatch(main, request)
	if type(request) ~= "table" or type(request.op) ~= "string" then
		return errorResponse("INPUT_INVALID", "request_validation", "Request must contain a string op")
	end
	if request.token ~= main.agentControlToken then
		return errorResponse("AUTH_REQUIRED", "authentication", "Invalid local bridge capability token")
	end
	if request.op == "status" then
		local activeBuildName
		if main.mode == "BUILD" and main.modes and main.modes["BUILD"] and main.modes["BUILD"].GetArgs then
			local _, name = main.modes["BUILD"]:GetArgs()
			activeBuildName = name
		end
		return { ok = true, result = {
			mode = main.mode, pendingMode = main.newMode,
			activeBuildName = activeBuildName,
			busy = main.popups and main.popups[1] ~= nil,
			processId = main.agentControlPid, protocolVersion = PROTOCOL_VERSION,
		} }
	elseif request.op == "show_items" then
		local buildMode = main.modes and main.modes["BUILD"]
		if main.mode ~= "BUILD" or type(buildMode) ~= "table" or type(buildMode.itemsTab) ~= "table" then
			return errorResponse("VALUE_UNAVAILABLE", "view_navigation", "PoB does not have an active build with an Items tab")
		end
		buildMode.viewMode = "ITEMS"
		local _, name = buildMode:GetArgs()
		return { ok = true, result = { viewMode = buildMode.viewMode, activeBuildName = name } }
	elseif request.op == "select_main_skill" then
		local buildMode = main.modes and main.modes["BUILD"]
		local skillName = type(request.arguments) == "table" and request.arguments.skillName
		if main.mode ~= "BUILD" or type(buildMode) ~= "table" or type(skillName) ~= "string" or skillName == "" then
			return errorResponse("INPUT_INVALID", "view_navigation", "An active build and skillName are required")
		end
		local control = buildMode.controls and buildMode.controls.mainSkill
		local matches = {}
		for index, entry in ipairs(control and control.list or {}) do
			local label = type(entry.label) == "string" and entry.label:gsub("%^[0-9A-Fa-f]", "") or ""
			if label:lower() == skillName:lower() then
				matches[#matches + 1] = { index = index, name = label }
			end
		end
		if #matches ~= 1 then
			return errorResponse("VALUE_UNAVAILABLE", "view_navigation", #matches == 0 and "Requested skill is not present in the main socket group" or "Requested skill name is ambiguous")
		end
		control:SetSel(matches[1].index)
		buildMode.viewMode = "CALCS"
		local _, activeBuildName = buildMode:GetArgs()
		return { ok = true, result = {
			activeBuildName = activeBuildName, viewMode = buildMode.viewMode,
			selectedSkill = matches[1].name, skillIndex = matches[1].index,
		} }
	elseif request.op == "list_builds" then
		return { ok = true, result = scanBuilds() }
	elseif request.op == "load_build" then
		local entry = findBuild(request.id)
		if not entry then return errorResponse("VALUE_UNAVAILABLE", "build_resolution", "Build ID is stale or unavailable") end
		if main.popups and main.popups[1] then
			return errorResponse("USER_ACTION_REQUIRED", "build_load", "Close the current PoB dialog before loading another build")
		end
		if not main:CanExit() then
			return errorResponse("USER_ACTION_REQUIRED", "build_load", "PoB requested a save decision; the current build was left open")
		end
		main:SetMode("BUILD", entry.id, entry.name)
		return { ok = true, result = { accepted = true, build = entry } }
	elseif request.op == "currentBuild" then
		local build, err = currentBuild(main)
		local player = build and build.calcsTab and build.calcsTab.mainEnv and build.calcsTab.mainEnv.player
		if not player then return errorResponse("VALUE_UNAVAILABLE", "current_build", err or "PoB calculation state is unavailable") end
		return { ok = true, result = { calcsTab = { mainEnv = { player = {} } } } }
	elseif request.op == "capture_snapshot" then
		local adapter = LoadModule("Modules/AgentInProcess")
		local result, err = adapter.dispatch("capture_snapshot", {}, main)
		if not result then return errorResponse("VALUE_UNAVAILABLE", "snapshot_capture", type(err) == "table" and err.message or tostring(err or "snapshot unavailable")) end
		return { ok = true, result = result }
	elseif request.op == "replace_item" or request.op == "replace_gem" or request.op == "change_passive" then
		return errorResponse("MUTATION_NOT_PERSISTENT", "bridge_capability", "Live PoB mutation is not enabled")
	elseif request.op == "compare_build_states" then
		local adapter = LoadModule("Modules/AgentInProcess")
		local args = type(request.arguments) == "table" and request.arguments or {}
		local result, err = adapter.dispatch(request.op, args, main)
		if not result then
			if type(err) == "table" then return { ok = false, error = err } end
			return errorResponse("VALUE_UNAVAILABLE", "tool_execution", tostring(err or "comparison failed"))
		end
		return { ok = true, result = result }
	elseif LoadModule("Modules/AgentBridge").isReadOnly(request.op) then
		local bridge = LoadModule("Modules/AgentBridge")
		local adapter = LoadModule("Modules/AgentInProcess")
		local build, buildErr = currentBuild(main)
		if not build then return errorResponse("VALUE_UNAVAILABLE", "current_build", buildErr or "running PoB build is unavailable") end
		local args = type(request.arguments) == "table" and request.arguments or {}
		local result, err = bridge.dispatch(build, { tool = request.op, arguments = args }, nil, function(_, toolName, arguments)
			return adapter.dispatch(toolName, arguments, main)
		end)
		if not result then
			if type(err) == "table" then return { ok = false, error = err } end
			return errorResponse("VALUE_UNAVAILABLE", "tool_execution", tostring(err or "PoB tool failed"))
		end
		return { ok = true, result = result }
	end
	return errorResponse("TOOL_NOT_FOUND", "tool_dispatch", "Unsupported local bridge operation")
end

local function closeClient(self)
	if self.client then pcall(function() self.client:close() end) end
	self.client = nil
	self.input = ""
	self.output = nil
	self.outputOffset = 1
	self.acceptedAt = nil
end

local function writeEndpoint(path, endpoint)
	local payload = encode(endpoint)
	if not payload then return nil, "Unable to encode endpoint metadata" end
	local temporaryPath = path .. ".tmp"
	local file, err = io.open(temporaryPath, "wb")
	if not file then return nil, err end
	local written, writeErr = file:write(payload)
	file:close()
	if not written then os.remove(temporaryPath); return nil, writeErr end
	os.remove(path)
	local renamed, renameErr = os.rename(temporaryPath, path)
	if not renamed then os.remove(temporaryPath); return nil, renameErr end
	return true
end

local Control = {}
Control.dispatchRequest = dispatch

function Control.new(main)
	if type(main.userPath) ~= "string" or main.userPath == "" then return nil, "PoB user path is unavailable" end
	local token, pid, randomErr = makeTokenAndPid()
	if not token then return nil, randomErr end
	local server, socketErr = socket.tcp4()
	if not server then return nil, socketErr end
	local bindHost = os.getenv("POB_AGENT_BIND_HOST") or "127.0.0.1"
	if bindHost ~= "127.0.0.1" and bindHost ~= "0.0.0.0" then
		server:close()
		return nil, "POB_AGENT_BIND_HOST must be 127.0.0.1 or 0.0.0.0"
	end
	local optionOk, optionErr = server:setoption("reuseaddr", true)
	if not optionOk then server:close(); return nil, optionErr end
	local bound, bindErr = server:bind(bindHost, 0)
	if not bound then server:close(); return nil, bindErr end
	local listening, listenErr = server:listen(4)
	if not listening then server:close(); return nil, listenErr end
	local _, port = server:getsockname()
	if type(port) ~= "number" then server:close(); return nil, "Unable to read local bridge port" end
	local endpointPath = main.userPath .. "AgentBridge-" .. tostring(pid) .. ".json"
	local endpointOk, endpointErr = writeEndpoint(endpointPath, {
		host = "127.0.0.1", port = port, token = token, processId = pid, protocolVersion = PROTOCOL_VERSION,
	})
	if not endpointOk then server:close(); return nil, endpointErr end
	local timeoutOk, timeoutErr = server:settimeout(0)
	if not timeoutOk then server:close(); os.remove(endpointPath); return nil, timeoutErr end
	main.agentControlToken = token
	main.agentControlPid = pid
	local self = { main = main, server = server, endpointPath = endpointPath, token = token }
	function self:OnFrame()
		if not self.client then
			local client = self.server:accept()
			if client then
				client:settimeout(0)
				self.client = client
				self.input = ""
				self.output = nil
				self.outputOffset = 1
				self.acceptedAt = socket.gettime()
			end
			return
		end
		if socket.gettime() - self.acceptedAt > CLIENT_TIMEOUT_SECONDS then closeClient(self); return end
		if not self.output then
			local line, receiveErr, partial = self.client:receive("*l")
			if partial and #partial > 0 then self.input = self.input .. partial end
			if #self.input > MAX_REQUEST_BYTES then
				self.output = encode(errorResponse("INPUT_INVALID", "request_validation", "Request exceeds the maximum frame size")) .. "\n"
			elseif line then
				self.input = self.input .. line
				if #self.input > MAX_REQUEST_BYTES then
					self.output = encode(errorResponse("INPUT_INVALID", "request_validation", "Request exceeds the maximum frame size")) .. "\n"
				else
					local request, _, decodeErr = json.decode(self.input)
					local response
					if not request then response = errorResponse("INPUT_INVALID", "request_validation", tostring(decodeErr or "Malformed JSON"))
					else
						local ok, result = pcall(dispatch, self.main, request)
						response = ok and result or errorResponse("BRIDGE_PROTOCOL_ERROR", "tool_execution", tostring(result))
					end
					self.output = encode(response)
					if not self.output or #self.output > MAX_RESPONSE_BYTES then
						self.output = encode(errorResponse("BRIDGE_PROTOCOL_ERROR", "response_encoding", "Response is too large or cannot be encoded"))
					end
					self.output = self.output .. "\n"
				end
			elseif receiveErr == "closed" then
				closeClient(self)
				return
		end
	end
	if self.output then
		local sent, sendErr, last = self.client:send(self.output, self.outputOffset)
		if sent then
			if sent >= #self.output then closeClient(self) else self.outputOffset = sent + 1 end
		elseif sendErr == "timeout" then
			if last and last >= self.outputOffset then self.outputOffset = last + 1 end
		elseif sendErr then
			closeClient(self)
		end
	end
	end
	function self:Shutdown()
		closeClient(self)
		if self.server then pcall(function() self.server:close() end); self.server = nil end
		os.remove(self.endpointPath)
		self.main.agentControlToken = nil
		self.main.agentControlPid = nil
	end
	return self
end

return Control
