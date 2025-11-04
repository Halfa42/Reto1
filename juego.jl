using Agents
using Genie, Genie.Renderer.Json

@agent struct Robot(GridAgent{2, Int})
    type::String = "Robot"
end

@agent struct Gallina(GridAgent{2, Int})
    type::String = "Gallina"
end

function agent_step!(a, model)
    if a isa Gallina
        randomwalk!(a, model)
    elseif a isa Robot
        # comportamiento del robot
    end
end

function initialize_model(; n_gallinas=3, dims=(20,20))
    space = GridSpace(dims, periodic=false)
    model = ABM(
        Union{Robot, Gallina},
        space;
        agent_step! = agent_step!
    )

    add_agent!((10,10), Robot, model)
    for _ in 1:n_gallinas
        pos = random_position(model)
        add_agent!(pos, Gallina, model)
    end

    return model
end

model = initialize_model()

route("/run") do
    run!(model, 1)
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

up(host="0.0.0.0", port=8000)
