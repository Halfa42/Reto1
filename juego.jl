using Agents
using Genie, Genie.Renderer.Json
using Random

@agent struct Robot(GridAgent{2, Int})
    type::String = "Robot"
end

@agent struct Gallina(GridAgent{2, Int})
    type::String = "Gallina"
    target::Tuple{Int, Int} # Nueva posición objetivo
    is_moving::Bool = false # Indica si se mueve a un target
end

function agent_step!(a, model)
    if a isa Gallina
        if !a.is_moving
            neighbor_positions = collect(nearby_positions(a.pos, model, 1)) # Posición válida si no se mueve
            if !isempty(neighbor_positions)
                a.target = rand(neighbor_positions)
                if a.target != a.pos
                    a.is_moving = true # ¡Iniciar el movimiento!
                end
            end
        else
            move_agent_single!(a, a.target, model) # Paso animado hacia el target
            if a.pos == a.target
                a.is_moving = false 
            end
        end
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
        add_agent!(pos, Gallina, model, "Gallina", pos, false)
    end

    return model
end

model = initialize_model()