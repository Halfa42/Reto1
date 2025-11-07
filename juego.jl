using Agents
using Genie, Genie.Renderer.Json
using Random
using LinearAlgebra # Necesario para la distancia

# --- CONSTANTES ---
# Radio de 5 celdas para que la gallina huya
const FLEE_RADIUS = 5.0 

# --- AGENTES ---
@agent struct Robot(GridAgent{2, Int})
    type::String = "Robot"
end

@agent struct Gallina(GridAgent{2, Int})
    type::String = "Gallina"
    target::Tuple{Int, Int} # Nueva posición objetivo
    is_moving::Bool = false # Indica si se mueve a un target
    speed_mode::String = "normal" # "normal" o "fleeing"
end

# --- LÓGICA DE PASO ---
function agent_step!(a, model)
    if a isa Gallina
        
        # 1. LÓGICA DE DECISIÓN (Solo si no se está moviendo a un target)
        if !a.is_moving
            # 1.1. Encontrar al robot
            robot = nothing
            # NOTA: No es necesario un collect() aquí, se puede iterar directo
            for agent in allagents(model)
                if agent isa Robot
                    robot = agent
                    break
                end
            end

            # 1.2. Si no hay robot, pasear normalmente
            if isnothing(robot)
                neighbor_positions = collect(nearby_positions(a.pos, model, 1))
                if !isempty(neighbor_positions)
                    a.target = rand(neighbor_positions)
                    if a.target != a.pos
                        a.is_moving = true
                    end
                end
                a.speed_mode = "normal"
                return # Termina el paso de esta gallina
            end

            # 1.3. Lógica de Huir vs. Pasear
            robot_pos = robot.pos
            current_distance = euclidean_distance(a.pos, robot_pos, model)
            # Solo consideramos movimientos a 1 celda de distancia
            possible_moves = collect(nearby_positions(a.pos, model, 1))

            if isempty(possible_moves) # Atrapada
                a.is_moving = false
                a.speed_mode = "normal"
                return
            end

            # 1.4. Clasificar movimientos (los que me alejan del radio de pánico)
            safe_moves = []
            for m in possible_moves
                # Un movimiento es "seguro" si está fuera del radio de pánico
                if euclidean_distance(m, robot_pos, model) >= FLEE_RADIUS
                    push!(safe_moves, m)
                end
            end

            # 1.5. Decidir Acción
            if current_distance < FLEE_RADIUS || isempty(safe_moves)
                # --- HUIR ---
                # (Está en peligro O no tiene movimientos seguros)
                # Escoge el movimiento que MAXIMICE la distancia al robot
                best_move = a.pos
                max_dist = current_distance
                
                for move in possible_moves
                    new_dist = euclidean_distance(move, robot_pos, model)
                    if new_dist > max_dist
                        max_dist = new_dist
                        best_move = move
                    end
                end
                
                if best_move != a.pos
                    a.target = best_move
                    a.is_moving = true
                    a.speed_mode = "fleeing" # ¡Aviso para que Python anime rápido!
                else
                    a.is_moving = false
                    a.speed_mode = "normal" # No hay a dónde huir
                end

            else
                # --- PASEAR ---
                # (Está segura Y tiene movimientos seguros)
                # Escoge un movimiento aleatorio de los seguros
                a.target = rand(safe_moves)
                if a.target != a.pos
                    a.is_moving = true
                end
                a.speed_mode = "normal"
            end
        
        # 2. LÓGICA DE MOVIMIENTO (Si ya tiene un target)
        else
            # Esto mueve al agente 1 celda EN EL GRID
            # La animación en Python debe cubrir esta distancia
            move_agent_single!(a, model) # Mueve 1 paso hacia el target
            
            # Si ya llegó al target, deja de moverse
            if a.pos == a.target
                a.is_moving = false
            end
        end

    elseif a isa Robot
        # El robot se controla desde Python, Julia no hace nada
        return
    end
end

# --- INICIALIZACIÓN ---
function initialize_model(; n_gallinas=3, dims=(20,20))
    space = GridSpace(dims, periodic=false)
    model = ABM(
        Union{Robot, Gallina},
        space;
        agent_step! = agent_step!
        # Ya no necesitamos properties, FLEE_RADIUS es una constante
    )

    add_agent!((10,10), Robot, model)
    for _ in 1:n_gallinas
        pos = random_position(model)
        # Añadimos los campos extra del struct Gallina
        add_agent!(pos, Gallina, model, "Gallina", pos, false, "normal")
    end

    return model
end

model = initialize_model()