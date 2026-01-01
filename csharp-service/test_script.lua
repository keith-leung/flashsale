-- Simple Lua script for wrk
wrk.method = "GET"
request = function()
    return wrk.format(nil, "/health")
end
