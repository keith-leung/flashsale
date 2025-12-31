wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = "{ invalid_json: "

request = function()
   return wrk.format(wrk.method, nil, nil, wrk.body)
end
