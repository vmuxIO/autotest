local mg     = require "moongen"
local memory = require "memory"
local device = require "device"
local ts     = require "timestamping"
local stats  = require "stats"
local hist   = require "histogram"

local PKT_SIZE	= 60
-- local ETH_DST	= "52:54:00:fa:00:60"
-- local ETH_DST	= "64:9d:99:b1:0b:59"
-- local ETH_DST	= "3e:30:b3:51:a3:76"
-- local ETH_DST    = "4e:6d:83:f0:73:84"

local function getRstFile(...)
	local args = { ... }
	for i, v in ipairs(args) do
		result, count = string.gsub(v, "%-%-result%=", "")
		if (count == 1) then
			return i, result
		end
	end
	return nil, nil
end

function configure(parser)
	parser:description("Generates bidirectional CBR traffic with hardware rate control and measure latencies.")
	parser:argument("dev", "Device to transmit/receive from."):convert(tonumber)
	parser:argument("mac", "MAC address of the destination device.")
	parser:option("-r --rate", "Transmit rate in Mbit/s."):default(10000):convert(tonumber)
	parser:option("-f --file", "Filename of the latency histogram."):default("histogram.csv")
end

function master(args)
	local dev = device.config({port = args.dev, rxQueues = 2, txQueues = 2})
	device.waitForLinks()
	dev:getTxQueue(0):setRate(args.rate)
	mg.startTask("loadSlave", dev:getTxQueue(0), dev:getMac(true), args.mac)
	stats.startStatsTask{dev}
	mg.startSharedTask("timerSlave", dev:getTxQueue(1), dev:getRxQueue(1), args.mac, args.file)
	mg.waitForTasks()
end

function loadSlave(queue, srcMac, dstMac)
	local mem = memory.createMemPool(function(buf)
		buf:getEthernetPacket():fill{
			ethSrc = srcMac,
			ethDst = dstMac,
			ethType = 0x1234
		}
	end)
	local bufs = mem:bufArray()
	while mg.running() do
		bufs:alloc(PKT_SIZE)
		queue:send(bufs)
	end
end

function timerSlave(txQueue, rxQueue, dstMac, histfile)
	local timestamper = ts:newTimestamper(txQueue, rxQueue)
	local hist = hist:new()
	mg.sleepMillis(1000) -- ensure that the load task is running
	while mg.running() do
		hist:update(timestamper:measureLatency(function(buf) buf:getEthernetPacket().eth.dst:setString(dstMac) end))
	end
	hist:print()
	hist:save(histfile)
end

