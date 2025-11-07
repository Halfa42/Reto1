include("juego.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs
using Agents

route("/run") do
    step!(model, agent_step!, 1)
    agents_data = [
        Dict(
            "id" => a.id,
            "type" => a.type,
            "pos" => a.pos
        ) for a in allagents(model)
    ]
    json(Dict("agents" => agents_data))
end

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

up(host="0.0.0.0", port=8000, async=false)