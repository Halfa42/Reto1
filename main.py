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

# Radio: 1 casilla Julia ≈ 11.6 OpenGL.
# Radio 4 en Julia ≈ 45 en OpenGL.
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

chickenCounter = 0
font = None
hunting = False

julia_queue = queue.Queue(maxsize=1)
julia_response_queue = queue.Queue(maxsize=1)
julia_thread_running = False

def check_boundaries(x, y, z, object_radius=0):
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
    norm_x = (grid_x - 1) / (GRID_SIZE - 1)
    norm_z = (grid_z - 1) / (GRID_SIZE - 1)
    opengl_x = X_MIN + norm_x * (X_MAX - X_MIN)
    opengl_z = Z_MIN + norm_z * (Z_MAX - Z_MIN)
    return opengl_x, opengl_z

def opengl_to_grid(opengl_x, opengl_z):
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
    global robot, gallinas, granja, granja_matrix, julia_thread_running, collision_handler, font, chickenCounter
    
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    font = pygame.font.SysFont("Arial", 32, bold=True)
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
    
    collision_handler = CollisionHandler()
    
    robot = Cuerpo(
        filepath="obj/robot/robot.obj",
        initial_pos=[0.0, 0.0, 0.0],
        scale=1.5
    )
    
    gallinas = []
    for i in range(10):
        g = Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[0.0, 0.0, 0.0], scale=2.5)
        gallinas.append(g)

    # Cargar granja
    # try:
    #     granja = OBJ(filename="obj/farm/granja.obj", swapyz=True)
    # except FileNotFoundError:
    #     granja = None
    
    # Matriz granja
    tx, ty, tz = 0.0, -5.0, 0.0
    sx = sy = sz = 7.0  
    m0 = sx; m5 = sy; m10 = sz
    granja_matrix = [m0, 0, 0, 0, 0, m5, 0, 0, 0, 0, m10, 0, tx, ty, tz, 1.0]

    try:
        load_texture("texturas/cielo.bmp")
    except Exception as e:
        print(f"Error Skybox: {e}")

    julia_thread_running = True
    thread = Thread(target=julia_communication_thread, daemon=True)
    thread.start()

def draw_text(text, x, y, color=(255,255,255)):
    global font

    # Crear superficie del texto
    surface = font.render(text, True, color)
    text_data = pygame.image.tostring(surface, "RGBA", True)
    width, height = surface.get_size()

    # Cambiar a proyección 2D
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, screen_width, 0, screen_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_TEXTURE_2D)

    # --- ARREGLO IMPORTANTE: alineamiento ---
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    # --- ARREGLO MEGA IMPORTANTE: soporte para alfa ---
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # (x,y) desde arriba
    glRasterPos2i(x, screen_height - y - height)

    glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glDisable(GL_BLEND)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

    glPopMatrix()  # MODELVIEW
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def try_pickup_chicken():
    global robot, gallinas

    if robot.hasChicken:
        return  # ya tiene una

    rx, _, rz = robot.position
    for gallina in gallinas:
        gx, _, gz = gallina.position
        dx = rx - gx
        dz = rz - gz
        dist = math.sqrt(dx*dx + dz*dz)

        if dist < 8.0:
            robot.hasChicken = True
            robot.takingChicken = True
            gallina.is_captured = True
            robot.captured_chicken = gallina
            return True

last_robot_grid_pos = None

def display(keys):
    global tick_counter, last_robot_grid_pos
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    if robot:
        rad = math.radians(robot.rotation_y)
        forward_x = math.cos(rad)
        forward_z = -math.sin(rad)
        
        distance_behind = 25.0
        camera_height = 15.0
        look_offset_y = 6.0
        
        eye_x = robot.position[0] - (forward_x * distance_behind)
        eye_y = robot.position[1] + camera_height
        eye_z = robot.position[2] - (forward_z * distance_behind)
        
        center_x = robot.position[0]
        center_y = robot.position[1] + look_offset_y
        center_z = robot.position[2]
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0.0, 1.0, 0.0)
    else:
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0, 50, 100, 0, 0, 0, 0, 1, 0)

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

    # Dibujar Granja (comentado por ahora por pruebas en Mac)
    # if granja:
    #     glPushMatrix()
    #     glMultMatrixf(granja_matrix)
    #     granja.render()
    #     glPopMatrix()
    
    if robot:
        robot.draw()

    # Envío a Julia
    if tick_counter % UPDATE_INTERVAL == 0 and robot:
        r_pos_gl = robot.position
        r_x_grid, r_z_grid = opengl_to_grid(r_pos_gl[0], r_pos_gl[2])
        robot_data = {"robot_x": r_x_grid, "robot_z": r_z_grid}
        try:
            julia_queue.put_nowait(robot_data)
        except queue.Full:
            pass
    
    try:
        data = julia_response_queue.get_nowait()
        for agent in data.get("agents", []):
            if agent["type"] == "Gallina":
                idx = agent["id"] - 2
                if 0 <= idx < len(gallinas):
                    grid_x, grid_z = agent["pos"]
                    new_x, new_z = grid_to_opengl(grid_x, grid_z)
                    
                    old_x = gallinas[idx].position[0]
                    old_z = gallinas[idx].position[2]
                    
                    new_x, _, new_z = check_boundaries(new_x, 10.0, new_z, object_radius=CHICKEN_COLLISION_RADIUS)
                    
                    valid_x, valid_z = collision_handler.get_valid_position(
                        old_x, old_z, new_x, new_z, entity_radius=CHICKEN_COLLISION_RADIUS
                    )
                    
                    gallinas[idx].update_from_julia(valid_x, valid_z)
                    
                    if "speed_mode" in agent:
                        gallinas[idx].set_speed_mode(agent["speed_mode"])
    except queue.Empty:
        pass
    
    for gallina in gallinas:
        if gallina.is_captured and robot:
            gallina.attached_to = (
                robot.position[0],
                robot.position[1] + robot.base_height,
                robot.position[2],
                robot.rotation_y
            )
        gallina.animate_step()
        gallina.draw(keys)

done = False
Init()
clock = pygame.time.Clock()

while not done:
    for event in pygame.event.get():  
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            done = True

    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE]:
        hunting = True
    if robot:
        # Guardar posición anterior
        old_x = robot.position[0]
        old_z = robot.position[2]
        
        # Calcular movimiento
        robot.move(keys)
        if try_pickup_chicken():
            chickenCounter += 1
        
        # Colisiones: (Descomentar al activar la granja)
        # new_x = robot.position[0]
        # new_z = robot.position[2]
        
        # # Verificar límites del mapa
        # new_x, new_y, new_z = check_boundaries(new_x, robot.position[1], new_z, object_radius=ROBOT_COLLISION_RADIUS)
        
        # # Verificar colisiones con obstáculos
        # valid_x, valid_z = collision_handler.get_valid_position(
        #     old_x, old_z, new_x, new_z, entity_radius=ROBOT_COLLISION_RADIUS
        # )
        
        # # Aplicar posición válida
        # robot.position[0] = valid_x
        # robot.position[1] = new_y
        # robot.position[2] = valid_z
        
    display(keys)
    tick_counter += 1
    draw_text(f"{chickenCounter}/10 gallinas recolectadas", 20, 20)
    pygame.display.flip()
    clock.tick(60)

julia_thread_running = False
pygame.quit()