using Agents
using Random

@agent struct Robot(GridAgent{2})
    type::String
end

@agent struct Gallina(GridAgent{2})
    type::String
    speed_mode::String
end

# Aprox 46 unidades OpenGL
const FLEE_RADIUS = 4.0 

function euclidean_distance(pos1, pos2)
    dx = pos1[1] - pos2[1]
    dy = pos1[2] - pos2[2]
    return sqrt(dx^2 + dy^2)
end

function flocking_step!(agent, model)
    neighbors = filter(a -> a isa Gallina, collect(nearby_agents(agent, model, 5)))
    
    if isempty(neighbors)
        if rand() < 0.7
            possible = collect(nearby_positions(agent.pos, model, 1))
            valid = [p for p in possible if isempty(p, model)]
            if !isempty(valid)
                move_agent!(agent, rand(valid), model)
            end
        end
        return
    end

    sum_x = 0.0
    sum_y = 0.0
    for mate in neighbors
        sum_x += mate.pos[1]
        sum_y += mate.pos[2]
    end
    center_x = sum_x / length(neighbors)
    center_y = sum_y / length(neighbors)
    center_pos = (center_x, center_y)

    dist_to_center = euclidean_distance(agent.pos, center_pos)
    
    force_random = dist_to_center < 2.0 
    
    if force_random || rand() < 0.4 
        possible = collect(nearby_positions(agent.pos, model, 1))
        valid = [p for p in possible if isempty(p, model)]
        if !isempty(valid)
            move_agent!(agent, rand(valid), model)
        end
    else
        possible_moves = collect(nearby_positions(agent.pos, model, 1))
        best_move = agent.pos
        min_dist = dist_to_center
        
        for move in possible_moves
            if isempty(move, model)
                d = euclidean_distance(move, center_pos)
                if d < min_dist
                    min_dist = d
                    best_move = move
                end
            end
        end
        
        if best_move != agent.pos
            move_agent!(agent, best_move, model)
        end
    end
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
            flocking_step!(agent, model)
            agent.speed_mode = "normal"
            return
        end

        dist_robot = euclidean_distance(agent.pos, robot.pos)
        
        if dist_robot < FLEE_RADIUS
            possible_moves = collect(nearby_positions(agent.pos, model, 1))
            valid_moves = [p for p in possible_moves if isempty(p, model)]
            
            if isempty(valid_moves)
                return 
            end

            # Si el robot está muy cerca, corre para salir
            if dist_robot < 2.0
                move_agent!(agent, rand(valid_moves), model)
                agent.speed_mode = "fleeing"
                return
            end

            best_move = agent.pos
            max_dist = dist_robot
            found_better = false
            
            for move in valid_moves
                new_dist = euclidean_distance(move, robot.pos)
                if new_dist > max_dist
                    max_dist = new_dist
                    best_move = move
                    found_better = true
                end
            end
            
            if found_better
                move_agent!(agent, best_move, model)
                agent.speed_mode = "fleeing"
            else
                move_agent!(agent, rand(valid_moves), model)
                agent.speed_mode = "fleeing"
            end

        else
            flocking_step!(agent, model)
            agent.speed_mode = "normal"
        end
    end
end

function initialize_model(; n_gallinas=10, dims=(20,20))
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