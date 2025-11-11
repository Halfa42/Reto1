include("juego.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP

route("/run", method=POST) do
    data = jsonpayload()
    
    if haskey(data, "robot_x") && haskey(data, "robot_z")
        robot_x = data["robot_x"]
        robot_z = data["robot_z"]
        
        robot_x = clamp(robot_x, 1, 20)
        robot_z = clamp(robot_z, 1, 20)
        
        for agent in allagents(model)
            if agent isa Robot
                if agent.pos != (robot_x, robot_z)
                    move_agent!(agent, (robot_x, robot_z), model)
                end
                break
            end
        end
    end
    
    step!(model, agent_step!, 1)
    
    agents_data = []
    for a in allagents(model)
        agent_dict = Dict(
            "id" => a.id,
            "type" => a.type,
            "pos" => a.pos
        )
        if a isa Gallina
            agent_dict["speed_mode"] = a.speed_mode
        end
        push!(agents_data, agent_dict)
    end
    
    json(Dict("agents" => agents_data))
end

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

up(host="0.0.0.0", port=8000, async=false)