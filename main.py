import pygame 
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import requests
from threading import Thread
import queue

from robot import Cuerpo
from gallina import Gallina
from objloader import OBJ
from collision_handler import CollisionHandler

screen_width = 1200
screen_height = 800
FOVY = 60.0
ZNEAR = 1.0
ZFAR = 900.0

GRID_SIZE = 20
DIMBOARD_X = 116.0
DIMBOARD_Z = 118.0

X_MIN, X_MAX = -DIMBOARD_X, DIMBOARD_X
Y_MIN, Y_MAX = -100, 200
Z_MIN, Z_MAX = -DIMBOARD_Z, DIMBOARD_Z

# Radios de colisión para cada entidad
ROBOT_COLLISION_RADIUS = 4.0
CHICKEN_COLLISION_RADIUS = 3.0

robot = None
gallinas = []
collision_handler = None

UPDATE_INTERVAL = 20
tick_counter = 0

granja = None
granja_matrix = None
textures = []
SkyboxSize = 245

julia_queue = queue.Queue(maxsize=1)
julia_response_queue = queue.Queue(maxsize=1)
julia_thread_running = False

def check_boundaries(x, y, z, object_radius=0):
    """Verifica y ajusta las coordenadas para que estén dentro de los límites"""
    x = max(X_MIN + object_radius, min(X_MAX - object_radius, x))
    y = max(Y_MIN, min(Y_MAX, y))
    z = max(Z_MIN + object_radius, min(Z_MAX - object_radius, z))
    return x, y, z

def load_texture(filepath):
    textures.append(glGenTextures(1))
    id = len(textures) - 1
    glBindTexture(GL_TEXTURE_2D, textures[id])
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    try:
        image = pygame.image.load(filepath).convert()
        w, h = image.get_rect().size
        image_data = pygame.image.tostring(image, "RGBA")
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
        glGenerateMipmap(GL_TEXTURE_2D)
    except FileNotFoundError:
        print(f"Advertencia: No se pudo cargar la textura {filepath}")

def draw_skybox_quad(vertices):
    tex_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    glBegin(GL_QUADS)
    for i in range(4):
        glTexCoord2f(tex_coords[i][0], tex_coords[i][1])
        glVertex3d(vertices[i][0], vertices[i][1], vertices[i][2])
    glEnd()

def draw_skybox():
    if not textures:
        return
    glBindTexture(GL_TEXTURE_2D, textures[0])
    half_size = SkyboxSize / 2
    faces = [
        [(-half_size, half_size, -half_size), (half_size, half_size, -half_size),
        (half_size, -half_size, -half_size), (-half_size, -half_size, -half_size)],
        [(half_size, half_size, half_size), (-half_size, half_size, half_size),
        (-half_size, -half_size, half_size), (half_size, -half_size, half_size)],
        [(-half_size, half_size, half_size), (-half_size, half_size, -half_size),
        (-half_size, -half_size, -half_size), (-half_size, -half_size, half_size)],
        [(half_size, half_size, -half_size), (half_size, half_size, half_size),
        (half_size, -half_size, half_size), (half_size, -half_size, -half_size)],
        [(-half_size, half_size, half_size), (half_size, half_size, half_size),
        (half_size, half_size, -half_size), (-half_size, half_size, -half_size)],
        [(-half_size, -half_size, half_size), (half_size, -half_size, half_size),
        (half_size, -half_size, -half_size), (-half_size, -half_size, -half_size)]
    ]
    for vertices in faces:
        draw_skybox_quad(vertices)

def grid_to_opengl(grid_x, grid_z):
    """Convierte coordenadas de grilla Julia (1-20) a OpenGL"""
    norm_x = (grid_x - 1) / (GRID_SIZE - 1)
    norm_z = (grid_z - 1) / (GRID_SIZE - 1)
    opengl_x = X_MIN + norm_x * (X_MAX - X_MIN)
    opengl_z = Z_MIN + norm_z * (Z_MAX - Z_MIN)
    return opengl_x, opengl_z

def opengl_to_grid(opengl_x, opengl_z):
    """Convierte coordenadas OpenGL a grilla Julia (1-20)"""
    opengl_x = max(X_MIN, min(X_MAX, opengl_x))
    opengl_z = max(Z_MIN, min(Z_MAX, opengl_z))
    norm_x = (opengl_x - X_MIN) / (X_MAX - X_MIN)
    norm_z = (opengl_z - Z_MIN) / (Z_MAX - Z_MIN)
    grid_x = int(norm_x * (GRID_SIZE - 1) + 1)
    grid_z = int(norm_z * (GRID_SIZE - 1) + 1)
    grid_x = max(1, min(GRID_SIZE, grid_x))
    grid_z = max(1, min(GRID_SIZE, grid_z))
    return grid_x, grid_z

def julia_communication_thread():
    """Thread separado para comunicación con Julia sin bloquear el render"""
    session = requests.Session()
    
    while julia_thread_running:
        try:
            robot_data = julia_queue.get(timeout=0.1)
            url = "http://localhost:8000/run"
            res = session.post(url, json=robot_data, timeout=3.0)
            
            if res.status_code == 200:
                data = res.json()
                try:
                    julia_response_queue.put_nowait(data)
                except queue.Full:
                    pass
        except queue.Empty:
            continue
        except Exception:
            continue

def Init():
    global robot, gallinas, granja, granja_matrix, julia_thread_running, collision_handler
    
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Control de Agentes")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width / screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    glClearColor(0.1, 0.1, 0.1, 1.0) 
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 200, 0, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.7, 0.7, 0.7, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.9, 0.9, 0.9, 1.0))
    
    glEnable(GL_COLOR_MATERIAL)
    
    # Inicializar sistema de colisiones
    collision_handler = CollisionHandler()
    
    # Robot con escala y posición original
    robot = Cuerpo(
        filepath="obj/robot/robot.obj",
        initial_pos=[0.0, 16.0, 0.0],
        scale=1.5
    )
    
    # Gallinas distribuidas por el mapa
    gallinas = [
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[-80.0, 10.0, -80.0], scale=2.5),
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[80.0, 10.0, -80.0], scale=2.5),
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[0.0, 10.0, 80.0], scale=2.5)
    ]

    # Cargar granja con escala 7.0 original
    try:
        granja = OBJ(filename="obj/farm/granja.obj", swapyz=True)
    except FileNotFoundError:
        print("Advertencia: No se pudo cargar obj/farm/granja.obj")
        granja = None
    
    tx, ty, tz = 0.0, -5.0, 0.0
    sx = sy = sz = 7.0  
    r = math.radians(0.0)
    s = math.radians(0.0)

    cos_r, sin_r = math.cos(r), math.sin(r)
    cos_s, sin_s = math.cos(s), math.sin(s)

    m0 = sx * (cos_r * cos_s - sin_r * sin_s)
    m2 = sx * (-cos_r * sin_s - sin_r * cos_s)
    m5 = sy
    m8 = sz * (sin_r * cos_s + cos_r * sin_s)
    m10 = sz * (-sin_r * sin_s + cos_r * cos_s)

    granja_matrix = [
        m0,  0.0,  m2,  0.0,
        0.0,   m5, 0.0,  0.0,
        m8,  0.0, m10,  0.0,
        tx,   ty,  tz,  1.0
    ]

    try:
        load_texture("texturas/cielo.bmp")
    except Exception as e:
        print(f"Advertencia: Error cargando textura del skybox: {e}")

    julia_thread_running = True
    thread = Thread(target=julia_communication_thread, daemon=True)
    thread.start()

last_robot_grid_pos = None

def display():
    global tick_counter, last_robot_grid_pos
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # Cámara dinámica siguiendo al robot
    eye_x, eye_y, eye_z = 0.0, 50.0, 100.0
    center_x, center_y, center_z = 0.0, 0.0, 0.0

    if robot:
        robot_x, robot_y, robot_z = robot.position
        
        if hasattr(robot, 'direction'):
            robot_dir_x = robot.direction[0]
            robot_dir_z = robot.direction[2]
        elif hasattr(robot, 'rotation_angle'):
            rad_angle = math.radians(robot.rotation_angle)
            robot_dir_x = math.sin(rad_angle)
            robot_dir_z = -math.cos(rad_angle)
        else:
            robot_dir_x = 0.0
            robot_dir_z = -1.0
            
        scale_factor = robot.scale_factor
        distance_behind = 15.0 * scale_factor
        height_offset = 10.0 * scale_factor
        eye_x = robot_x - robot_dir_x * distance_behind
        eye_y = robot_y + height_offset
        eye_z = robot_z - robot_dir_z * distance_behind
        look_ahead_distance = distance_behind * 1.5
        center_x = robot_x + robot_dir_x * look_ahead_distance
        center_y = robot_y + height_offset * 0.5
        center_z = robot_z + robot_dir_z * look_ahead_distance
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0.0, 1.0, 0.0)

    # Skybox
    glPushMatrix()
    glDisable(GL_LIGHTING)   
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D) 
    draw_skybox()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D) 
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)    
    glPopMatrix()

    # Granja
    if granja:
        glPushMatrix()
        glMultMatrixf(granja_matrix)
        granja.render()
        glPopMatrix()
    
    # Dibujar robot
    if robot:
        robot.draw()

    # Enviar posición del robot a Julia
    if tick_counter % UPDATE_INTERVAL == 0 and robot:
        r_pos_gl = robot.position
        r_x_grid, r_z_grid = opengl_to_grid(r_pos_gl[0], r_pos_gl[2])
        
        current_pos = (r_x_grid, r_z_grid)
        if current_pos != last_robot_grid_pos:
            last_robot_grid_pos = current_pos
            robot_data = {"robot_x": r_x_grid, "robot_z": r_z_grid}
            
            try:
                julia_queue.put_nowait(robot_data)
            except queue.Full:
                pass
    
    # Recibir actualizaciones de Julia para las gallinas
    try:
        data = julia_response_queue.get_nowait()
        for agent in data.get("agents", []):
            if agent["type"] == "Gallina":
                idx = agent["id"] - 2
                if 0 <= idx < len(gallinas):
                    grid_x, grid_z = agent["pos"]
                    new_x, new_z = grid_to_opengl(grid_x, grid_z)
                    
                    # Guardar posición anterior de la gallina
                    old_x = gallinas[idx].position[0]
                    old_z = gallinas[idx].position[2]
                    
                    # Aplicar límites de boundaries
                    new_x, _, new_z = check_boundaries(new_x, 10.0, new_z, object_radius=CHICKEN_COLLISION_RADIUS)
                    
                    # Verificar colisiones con el collision handler
                    valid_x, valid_z = collision_handler.get_valid_position(
                        old_x, old_z, new_x, new_z, entity_radius=CHICKEN_COLLISION_RADIUS
                    )
                    
                    # Actualizar posición solo si es válida
                    gallinas[idx].update_from_julia(valid_x, valid_z)
                    
                    if "speed_mode" in agent:
                        gallinas[idx].set_speed_mode(agent["speed_mode"])
    except queue.Empty:
        pass
    
    # Dibujar gallinas
    for gallina in gallinas:
        gallina.animate_step()
        gallina.draw()

done = False
Init()
clock = pygame.time.Clock()

while not done:
    for event in pygame.event.get():  
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            done = True

    keys = pygame.key.get_pressed()
    
    if robot:
        # Guardar posición anterior del robot
        old_x = robot.position[0]
        old_z = robot.position[2]
        
        # Aplicar movimiento original
        robot.move(keys)
        
        # Verificar colisiones y ajustar posición del robot
        new_x = robot.position[0]
        new_z = robot.position[2]
        
        # Verificar límites
        new_x, new_y, new_z = check_boundaries(new_x, robot.position[1], new_z, object_radius=ROBOT_COLLISION_RADIUS)
        
        # Verificar colisiones con lago y obstáculos
        valid_x, valid_z = collision_handler.get_valid_position(
            old_x, old_z, new_x, new_z, entity_radius=ROBOT_COLLISION_RADIUS
        )
        
        # Aplicar posición válida
        robot.position[0] = valid_x
        robot.position[1] = new_y
        robot.position[2] = valid_z
    
    display()
    tick_counter += 1
    
    pygame.display.flip()
    clock.tick(60)

julia_thread_running = False
pygame.quit()