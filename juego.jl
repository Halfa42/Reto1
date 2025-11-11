using Agents
using Random

@agent struct Robot(GridAgent{2})
    type::String
end

@agent struct Gallina(GridAgent{2})
    type::String
    speed_mode::String
end

const FLEE_RADIUS = 5.0

function euclidean_distance(pos1, pos2)
    dx = pos1[1] - pos2[1]
    dy = pos1[2] - pos2[2]
    return sqrt(dx^2 + dy^2)
end

function agent_step!(agent, model)
    if agent isa Gallina
        robot = nothing
        for a in allagents(model)
            if a isa Robot
                robot = a
                break
            end
        end

        if isnothing(robot)
            neighbor_positions = collect(nearby_positions(agent.pos, model, 1))
            valid_moves = [pos for pos in neighbor_positions if isempty(pos, model)]
            if !isempty(valid_moves)
                move_agent!(agent, rand(valid_moves), model)
                agent.speed_mode = "normal"
            end
            return
        end

        current_distance = euclidean_distance(agent.pos, robot.pos)
        
        if current_distance < FLEE_RADIUS
            possible_moves = collect(nearby_positions(agent.pos, model, 1))
            best_move = agent.pos
            max_dist = current_distance
            
            for move in possible_moves
                if isempty(move, model)
                    new_dist = euclidean_distance(move, robot.pos)
                    if new_dist > max_dist
                        max_dist = new_dist
                        best_move = move
                    end
                end
            end
            
            if best_move != agent.pos
                move_agent!(agent, best_move, model)
                agent.speed_mode = "fleeing"
            else
                agent.speed_mode = "normal"
            end
        else
            neighbor_positions = collect(nearby_positions(agent.pos, model, 1))
            valid_moves = [pos for pos in neighbor_positions if isempty(pos, model)]
            if !isempty(valid_moves)
                move_agent!(agent, rand(valid_moves), model)
                agent.speed_mode = "normal"
            end
        end
    end
end

function initialize_model(; n_gallinas=3, dims=(20,20))
    space = GridSpace(dims, periodic=false)
    model = ABM(Union{Gallina, Robot}, space; agent_step!)

    add_agent!((10,10), Robot, model; type="Robot")
    
    for _ in 1:n_gallinas
        pos = (rand(1:dims[1]), rand(1:dims[2]))
        while euclidean_distance(pos, (10,10)) < 5
            pos = (rand(1:dims[1]), rand(1:dims[2]))
        end
        add_agent!(pos, Gallina, model; type="Gallina", speed_mode="normal")
    end

    return model
end

global model = initialize_model()