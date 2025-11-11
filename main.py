import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import requests

from robot import Cuerpo
from gallina import Gallina

screen_width = 1200
screen_height = 800
FOVY = 60.0
ZNEAR = 1.0
ZFAR = 900.0

EYE_X = 300.0
EYE_Y = 200.0
EYE_Z = 60.0
CENTER_X = 0.0
CENTER_Y = 5.0
CENTER_Z = 0.0
UP_X = 0.0
UP_Y = 1.0
UP_Z = 0.0

DimBoard = 300
X_MIN, X_MAX = -500, 500
Y_MIN, Y_MAX = -500, 500
Z_MIN, Z_MAX = -500, 500

robot = None
gallinas = []

UPDATE_INTERVAL = 20
tick_counter = 0

def Axis():
    glShadeModel(GL_FLAT)
    glLineWidth(3.0)
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN, 0.0, 0.0)
    glVertex3f(X_MAX, 0.0, 0.0)
    glEnd()
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, Y_MIN, 0.0)
    glVertex3f(0.0, Y_MAX, 0.0)
    glEnd()
    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, Z_MIN)
    glVertex3f(0.0, 0.0, Z_MAX)
    glEnd()
    glLineWidth(1.0)

def Init():
    global robot, gallinas
    
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
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
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[-50.0, 0.0, -50.0], scale=2.5),
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[50.0, 0.0, -50.0], scale=2.5),
        Gallina(filepath="obj/gallina/gallina.obj", initial_pos=[0.0, 0.0, 50.0], scale=2.5)
    ]

def display():
    global tick_counter
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    Axis()
    
    glColor3f(0.4, 0.4, 0.4)
    glBegin(GL_QUADS)
    glVertex3d(-DimBoard, 0, -DimBoard)
    glVertex3d(-DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, -DimBoard)
    glEnd()
    
    if robot:
        robot.draw()

    if tick_counter % UPDATE_INTERVAL == 0:
        try:
            r_pos_gl = robot.position
            r_x_grid = int(((r_pos_gl[0] + 100) / 200) * 19 + 1)
            r_z_grid = int(((r_pos_gl[2] + 100) / 200) * 19 + 1)
            r_x_grid = max(1, min(20, r_x_grid))
            r_z_grid = max(1, min(20, r_z_grid))
            
            url = "http://localhost:8000/run"
            robot_data = {"robot_x": r_x_grid, "robot_z": r_z_grid}
            
            res = requests.post(url, json=robot_data, timeout=2.0)
            
            if res.status_code == 200:
                data = res.json()
                for agent in data["agents"]:
                    if agent["type"] == "Gallina":
                        idx = agent["id"] - 2
                        if 0 <= idx < len(gallinas):
                            x, y = agent["pos"]
                            new_x = (x - 10) * 10
                            new_z = (y - 10) * 10
                            gallinas[idx].update_from_julia(new_x, new_z)
                            if "speed_mode" in agent:
                                gallinas[idx].set_speed_mode(agent["speed_mode"])
        except:
            pass
    
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
        robot.move(keys)
    
    display()
    tick_counter += 1
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()