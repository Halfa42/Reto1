import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math

from objloader import OBJ

# Se importa la clases principales
# from gallina import Gallina
from robot import Cuerpo

# --- Configuracion de la Ventana y Camara ---
screen_width = 1200
screen_height = 800
FOVY = 60.0
ZNEAR = 1.0
ZFAR = 900.0

# --- Configuracion del Entorno ---
DimBoard = 300
X_MIN, X_MAX = -500, 500
Y_MIN, Y_MAX = -500, 500
Z_MIN, Z_MAX = -500, 500

# Objeto principal
robot = None
gallina = None # Se deja la variable pero no se usara

# --- Nuevas variables para la granja ---
granja = None
granja_matrix = None

# --- Variables para el Skybox ---
textures = []
SkyboxSize = 240

# Variables para el texto en pantalla

chickenCounter = 0
font = None

# Funciones para el Skybox ---

def load_texture(filepath):
    """Carga una textura desde un archivo y la añade a la lista global."""
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
        print(f"Error: No se pudo cargar la textura {filepath}")
        raise

def draw_skybox_quad(vertices):
    """Dibuja un solo quad del skybox."""
    tex_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    glBegin(GL_QUADS)
    for i in range(4):
        glTexCoord2f(tex_coords[i][0], tex_coords[i][1])
        glVertex3d(vertices[i][0], vertices[i][1], vertices[i][2])
    glEnd()

def draw_skybox():
    """Dibuja las 6 caras del skybox."""
    # Usar textures[0] porque es la primera (y unica) que cargamos
    glBindTexture(GL_TEXTURE_2D, textures[0])
    half_size = SkyboxSize / 2
    faces = [
        # Cara frontal
        [(-half_size, half_size, -half_size), (half_size, half_size, -half_size),
         (half_size, -half_size, -half_size), (-half_size, -half_size, -half_size)],
        # Cara trasera
        [(half_size, half_size, half_size), (-half_size, half_size, half_size),
         (-half_size, -half_size, half_size), (half_size, -half_size, half_size)],
        # Cara izquierda
        [(-half_size, half_size, half_size), (-half_size, half_size, -half_size),
         (-half_size, -half_size, -half_size), (-half_size, -half_size, half_size)],
        # Cara derecha
        [(half_size, half_size, -half_size), (half_size, half_size, half_size),
         (half_size, -half_size, half_size), (half_size, -half_size, -half_size)],
        # Cara superior
        [(-half_size, half_size, half_size), (half_size, half_size, half_size),
         (half_size, half_size, -half_size), (-half_size, half_size, -half_size)],
        # Cara inferior
        [(-half_size, -half_size, half_size), (half_size, -half_size, half_size),
         (half_size, -half_size, -half_size), (-half_size, -half_size, -half_size)]
    ]
    for vertices in faces:
        draw_skybox_quad(vertices)

def Init():
    """ Funcion de inicializacion general. """
    global robot
    global gallina
    global granja, granja_matrix # Hacer globales las nuevas variables
    global font
    global chickenCounter

    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont("Arial", 32, bold=True)

    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Captura las Gallinas")

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

    # Creación del robot
    robot = Cuerpo(
        filepath="obj/robot/robot.obj",
        initial_pos=[0.0, 18.0, 0.0],
        scale=1.5
    )

    # Creación de la gallina
    # gallina = Gallina(
    #     filepath="obj/gallina/gallina.obj",
    #     initial_pos=[0.0, 0.0, 0.0],
    #     scale=3.0
    # )
    
    # --- Cargar la Granja ---
    try:
        granja = OBJ(filename="obj/farm/granja.obj", swapyz=True)
    except FileNotFoundError:
        print("Error: No se pudo cargar obj/farm/granja.obj")
        granja = None
    
    # Pre-calcular la matriz de transformacion para la granja
    tx, ty, tz = 0.0, 0.0, 0.0
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

    # Cargar textura del Skybox ---
    try:
        load_texture("texturas/cielo.bmp")
    except Exception as e:
        print(f"Error cargando la textura del skybox: {e}")

# Función para mostrar texto en la pantalla

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


def display():
    """ Funcion de dibujado de cada fotograma. """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # --- Logica de Camara ---
    
    # Valores por defecto si el robot no existe
    eye_x, eye_y, eye_z = 0.0, 40.0, 60.0 
    center_x, center_y, center_z = 0.0, 5.0, 0.0

    if robot:
        robot_x, robot_y, robot_z = robot.position
        robot_dir_x = robot.direction[0]
        robot_dir_z = robot.direction[2]
        scale_factor = robot.scale_factor
        distance_behind_factor = 12.0
        height_offset_factor = 8.0
        distance_behind = distance_behind_factor * scale_factor
        height_offset = height_offset_factor * scale_factor
        eye_x = robot_x - robot_dir_x * distance_behind
        eye_y = robot_y + height_offset
        eye_z = robot_z - robot_dir_z * distance_behind
        look_ahead_distance = distance_behind * 2.0
        center_x = robot_x + robot_dir_x * look_ahead_distance
        center_y = robot_y + height_offset
        center_z = robot_z + robot_dir_z * look_ahead_distance
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(eye_x, eye_y, eye_z, 
              center_x, center_y, center_z, 
              0.0, 1.0, 0.0)

    # --- Dibujar Skybox ---
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

    # --- Dibujar la Granja ---
    if granja:
        glPushMatrix()
        glMultMatrixf(granja_matrix)
        granja.render()
        glPopMatrix()
    
    # Dibujar al robot
    if robot:
        robot.draw()

    # Dibujar la gallina 
    # if gallina:
    #     gallina.draw()

# --- Bucle Principal ---
done = False
Init()
clock = pygame.time.Clock()

while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            done = True

    keys = pygame.key.get_pressed()

    # Actualizar el estado del robot
    if robot:
        robot.move(keys)

    # Renderizar la escena
    display()

    draw_text(f"hasChicken: {robot.hasChicken}", 20, 20)

    pygame.display.flip()

    clock.tick(60)

pygame.quit()