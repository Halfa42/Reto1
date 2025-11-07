import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import requests

# Se importa la clases principales
from robot import Cuerpo
from gallina import Gallina


# --- Configuracion de la Ventana y Camara ---
screen_width = 1200
screen_height = 800
FOVY = 60.0
ZNEAR = 1.0
ZFAR = 900.0

# --- Posicion de la Camara Fija ---
EYE_X = 300.0
EYE_Y = 200.0
EYE_Z = 60.0
CENTER_X = 0.0
CENTER_Y = 5.0
CENTER_Z = 0.0
UP_X = 0.0
UP_Y = 1.0
UP_Z = 0.0

# --- Configuracion del Entorno ---
DimBoard = 300
X_MIN, X_MAX = -500, 500
Y_MIN, Y_MAX = -500, 500
Z_MIN, Z_MAX = -500, 500

# Objeto principal 
robot = None
# gallina = None

def Axis():
    """ Dibuja los ejes X (rojo), Y (verde) y Z (azul). """
    glShadeModel(GL_FLAT)
    glLineWidth(3.0)
    # Eje X en rojo
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN, 0.0, 0.0)
    glVertex3f(X_MAX, 0.0, 0.0)
    glEnd()
    # Eje Y en verde
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, Y_MIN, 0.0)
    glVertex3f(0.0, Y_MAX, 0.0)
    glEnd()
    # Eje Z en azul
    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, Z_MIN)
    glVertex3f(0.0, 0.0, Z_MAX)
    glEnd()
    glLineWidth(1.0)

def Init():
    """ Funcion de inicializacion general. """
    global robot, gallinas
    # global gallina
    
    pygame.init()
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Control de Agentes")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width / screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(EYE_X, EYE_Y, EYE_Z, CENTER_X, CENTER_Y, CENTER_Z, UP_X, UP_Y, UP_Z)
    
    glClearColor(0.1, 0.1, 0.1, 1.0) 
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 200, 0, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.7, 0.7, 0.7, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.9, 0.9, 0.9, 1.0))
    
    glEnable(GL_COLOR_MATERIAL)

    robot = Cuerpo(
        filepath="obj/robot/robot.obj",
        initial_pos=[0.0, 0.0, 0.0], 
        scale=3.0
    )
    gallinas = [
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[10*i, 0.0, 10*i], scale=2.5)
        for i in range(3)
    ]
    
    # Se crea una instancia de la gallina
    # gallina = Gallina(
    #     filepath="obj/gallina/gallina.obj",
    #     initial_pos=[0.0, 0.0, 0.0], 
    #     scale=3.0  # Usando la misma escala que el robot
    # )

def display():
    """ Funcion de dibujado de cada fotograma. """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    Axis()
    
    # Plano del suelo
    glColor3f(0.4, 0.4, 0.4)
    glBegin(GL_QUADS)
    glVertex3d(-DimBoard, 0, -DimBoard)
    glVertex3d(-DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, -DimBoard)
    glEnd()
    
    # Dibujar al robot
    if robot:
        robot.draw()

    # Actualizar posiciones desde Julia
    try:
        res = requests.get("http://localhost:8000/run")
        data = res.json()
        for agent in data["agents"]:
            if agent["type"] == "Gallina":
                idx = agent["id"] - 2  # id 1 = robot, los demás gallinas
                if 0 <= idx < len(gallinas):
                    x, y = agent["pos"]
                    gallinas[idx].update_from_julia(x*10, y*10) # *10 para escalar el Grid
    except Exception as e:
        pass
    
    # Dibujar la gallina
    for gallina in gallinas:
        gallina.animate_step()
        gallina.draw()  
    
    # res = requests.get("http://10.50.129.157:8000/run")
    # data = res.json()
    # for agent in data['agents']:
    #     gallina = gallinas[agent['id'] - 1]
    #     gallina.update(agent['pos'][0] * 10, agent['pos'][1] * 10)

# --- Bucle Principal ---
done = False
Init()
clock = pygame.time.Clock()

while not done:
    for event in pygame.event.get():  
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            done = True

    keys = pygame.key.get_pressed()
    
    # Actualizar el estado del robot (comentado)
    if robot:
        robot.move(keys)
        
    # Actualizar el estado de la gallina
    # if gallina:
    #     gallina.move(keys)
    
    # Renderizar la escena
    display()
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()