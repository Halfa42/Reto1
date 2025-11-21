import pygame
from OpenGL.GL import *
import math

from objloader import OBJ

class Brazo:
    """
    Gestiona el estado y el renderizado de un brazo del robot,
    incluyendo su movimiento de balanceo.
    """
    def __init__(self, filepath):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except FileNotFoundError:
            print(f"Error: No se pudo cargar el modelo 3D desde {filepath}")
            self.obj = None
        
        self.swing_angle = 0.0
        self.swing_direction = 1
        self.swing_speed = 2.5 # Grados por fotograma

    def update(self, is_moving, hasChicken):
        """
        Actualiza el ángulo del brazo. Si el robot se mueve, se balancea.
        Si está quieto, regresa a su posición original.
        """

        if hasChicken:
            self.swing_angle = -90
            return
        if not is_moving:
            # Regresar suavemente a la posicion inicial
            if abs(self.swing_angle) > self.swing_speed:
                self.swing_angle -= math.copysign(self.swing_speed, self.swing_angle)
            else:
                self.swing_angle = 0
            return

        self.swing_angle += self.swing_speed * self.swing_direction
        
        # Invertir la direccion del balanceo al alcanzar el límite de 45 grados
        if abs(self.swing_angle) > 45.0:
            self.swing_direction *= -1

    def draw(self, position_offset, invert_swing=False):
        """
        Dibuja el brazo. Un nuevo parametro 'invert_swing' permite
        negar el angulo para el movimiento opuesto.
        """
        if not self.obj:
            return
            
        glPushMatrix()
                
        # Determina el angulo a usar, aplicando la inversion si es necesario
        if invert_swing and self.swing_angle != -90:
            angle_to_use = -self.swing_angle
        else:
            angle_to_use = self.swing_angle

        angle_rad = math.radians(angle_to_use)
        
        tx, ty, tz = position_offset
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # La matriz se mantiene identica, solo cambian los valores de cos_a y sin_a
        brazo_matrix = [
            1.0,   0.0,    0.0,   0.0,
            0.0, cos_a,  -sin_a,  0.0,
            0.0, sin_a,   cos_a,  0.0,
             tx,    ty,      tz,  1.0
        ]
        
        glMultMatrixf(brazo_matrix)
        
        self.obj.render()
        
        glPopMatrix()


class Cuerpo:
    """
    Clase principal del robot. Gestiona el estado general, el movimiento,
    la posicion y contiene las instancias de los brazos.
    """
    def __init__(self, filepath, initial_pos, scale):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except FileNotFoundError:
            print(f"Error: No se pudo cargar el modelo 3D desde {filepath}")
            self.obj = None
            
        self.position = list(initial_pos)
        self.scale_factor = scale
        self.rotation_y = 0.0
        
        self.speed = 0.7
        self.turn_speed = 2.0
        
        self.hasChicken = False
        self.takingChicken = False
        self.vertical_bob = 0.0
        self.bob_angle = 0.0
        self.bob_speed = 8.0 
        self.bob_height = 1.0
        
        self.base_height = 6.5
        
        self.brazo_izq = Brazo(filepath="obj/robot/brazoizq.obj")
        self.brazo_der = Brazo(filepath="obj/robot/brazoder.obj")
        
        offset_x = 0.75
        offset_y = -0.4
        offset_z = 0.0
        
        self.offset_brazo_izq = [offset_x, offset_y, offset_z]
        self.offset_brazo_der = [-offset_x, offset_y, offset_z]
        
        # --- Camara ---
        # Almacena el vector de direccion [x, y, z]
        self.direction = [0.0, 0.0, 0.0]
        self.update_direction() # Inicializarlo

        # --- Imprimir posicion ---
        self.last_known_position = list(self.position)

    # Nueva funcion auxiliar para actualizar la direccion
    def update_direction(self):
        """
        Calcula el vector de direccion frontal basado en la rotacion_y.
        """
        rad = math.radians(self.rotation_y)
        self.direction[0] = math.cos(rad)
        self.direction[2] = -math.sin(rad)

    def move(self, keys):
        """
        Procesa la entrada del teclado para actualizar el estado del robot.
        """
        is_moving = False
        is_moving_forward = False

        if keys[pygame.K_LEFT]:
            self.rotation_y += self.turn_speed
        if keys[pygame.K_RIGHT]:
            self.rotation_y -= self.turn_speed
        if keys[pygame.K_q]:
            self.hasChicken = False
        if keys[pygame.K_e]:
            self.hasChicken = True
        if keys[pygame.K_f]:
            self.takingChicken = True
            
        # --- Camara ---
        # Actualizar el vector de direccion DESPUES de cambiar la rotacion
        self.update_direction()
        dir_x = self.direction[0]
        dir_z = self.direction[2]
        
        if keys[pygame.K_UP]:
            self.position[0] += dir_x * self.speed
            self.position[2] += dir_z * self.speed
            is_moving = True
            is_moving_forward = True
        if keys[pygame.K_DOWN]:
            self.position[0] -= dir_x * self.speed
            self.position[2] -= dir_z * self.speed
            is_moving = True

        if is_moving_forward:
            self.bob_angle = (
                (self.bob_angle + self.bob_speed) % 360
                if not self.hasChicken
                else (self.bob_angle + self.bob_speed * 0.6) % 360
            )
            height = self.bob_height if not self.hasChicken else (self.bob_height * 0.4)

            self.vertical_bob = abs(math.sin(math.radians(self.bob_angle))) * height

        else:
            if self.vertical_bob > 0.1:
                self.vertical_bob -= 0.1
            else:
                self.vertical_bob = 0
                self.bob_angle = 0

        
        # --- Imprimir posicion (en caso de uso)---
        # if self.position != self.last_known_position:
        #     print(f"Robot en: x={self.position[0]:.2f}, y={self.position[1]:.2f}, z={self.position[2]:.2f}")
        #     self.last_known_position = list(self.position) 
        
        self.brazo_izq.update(is_moving, self.hasChicken)
        self.brazo_der.update(is_moving, self.hasChicken)

    def draw(self):
        """
        Dibuja el cuerpo del robot y luego a sus brazos hijos.
        """
        if not self.obj:
            return
            
        glPushMatrix()
        
        tx, ty, tz = self.position
        ty += self.base_height + self.vertical_bob
        sx = sy = sz = self.scale_factor
        r = math.radians(self.rotation_y)
        s = math.radians(-90.0)

        cos_r, sin_r = math.cos(r), math.sin(r)
        cos_s, sin_s = math.cos(s), math.sin(s)

        m0 = sx * (cos_r * cos_s - sin_r * sin_s)
        m2 = sx * (-cos_r * sin_s - sin_r * cos_s)
        m5 = sy
        m8 = sz * (sin_r * cos_s + cos_r * sin_s)
        m10 = sz * (-sin_r * sin_s + cos_r * cos_s)

        cuerpo_matrix = [
            m0,  0.0,  m2,  0.0,
           0.0,   m5, 0.0,  0.0,
            m8,  0.0, m10,  0.0,
            tx,   ty,  tz,  1.0
        ]
        
        glMultMatrixf(cuerpo_matrix)
        
        self.obj.render()
        
        self.brazo_izq.draw(self.offset_brazo_izq)
        self.brazo_der.draw(self.offset_brazo_der, invert_swing=True)
        
        glPopMatrix()