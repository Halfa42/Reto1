import pygame
from OpenGL.GL import *
import math

from objloader import OBJ

class Ala:
    """
    Gestiona el estado y renderizado de un ala de la gallina.
    Se mueven simétricamente (ambas suben o ambas bajan) y
    se abren en el eje Y.
    """
    def __init__(self, filepath):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except FileNotFoundError:
            print(f"Error: No se pudo cargar el modelo 3D desde {filepath}")
            self.obj = None
        
        self.flap_phase = 0.0
        self.flap_direction = 1
        self.flap_speed = 3.0       # Grados por fotograma
        self.flap_max_angle = 30.0  # Ángulo máximo 

    def update(self, is_moving):
        """
        Actualiza el ángulo del ala. Si la gallina se mueve, aletea.
        Si está quieta, regresa a su posición original.
        """
        if not is_moving:
            if abs(self.flap_phase) > self.flap_speed:
                self.flap_phase -= math.copysign(self.flap_speed, self.flap_phase)
            else:
                self.flap_phase = 0
            return

        self.flap_phase += self.flap_speed * self.flap_direction

        if abs(self.flap_phase) > self.flap_max_angle:
            self.flap_direction *= -1

    def draw(self, position_offset, invert_sweep=False):
        """
        Dibuja el ala usando una matriz de transformación pre-calculada
        que combina la rotación en X (aleteo) y en Y (abrir/cerrar).
        'invert_sweep' se usa para que un ala rote en +Y y la otra en -Y.
        """
        if not self.obj:
            return
            
        glPushMatrix()
        
        tx, ty, tz = position_offset

        angle_x_flap = abs(self.flap_phase)

        angle_y_sweep_amount = abs(self.flap_phase) * 0.5
        
        angle_y_sweep = angle_y_sweep_amount if invert_sweep else -angle_y_sweep_amount
        
        # --- Pre-cálculo de la Matriz ---
        angle_x_rad = math.radians(angle_x_flap)
        angle_y_rad = math.radians(angle_y_sweep)
        
        cos_x = math.cos(angle_x_rad)
        sin_x = math.sin(angle_x_rad)
        cos_y = math.cos(angle_y_rad)
        sin_y = math.sin(angle_y_rad)
        
        m0 = cos_y
        m2 = sin_y
        
        m4 = sin_y * sin_x
        m5 = cos_x
        m6 = -cos_y * sin_x        

        m8 = -sin_y * cos_x
        m9 = sin_x
        m10 = cos_y * cos_x
        
        ala_matrix = [
            m0,  0.0,  m2,  0.0,
            m4,  m5,   m6,  0.0,
            m8,  m9,   m10, 0.0,
            tx,  ty,   tz,  1.0
        ]
        
        glMultMatrixf(ala_matrix)
        
        self.obj.render()
        
        glPopMatrix()


class Pata:
    """
    Gestiona el estado y renderizado de una pata de la gallina.
    Realiza un movimiento de marcha alterno.
    """
    def __init__(self, filepath):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except FileNotFoundError:
            print(f"Error: No se pudo cargar el modelo 3D desde {filepath}")
            self.obj = None
        
        self.march_angle = 0.0
        self.march_direction = 1
        self.march_speed = 4.0       # Grados por fotograma
        self.march_max_angle = 20.0  # Límite de 20 grados
        self.return_speed = 6.0      # Velocidad de retorno a 0

    def update(self, is_moving):
        """
        Actualiza el ángulo de la pata. Si se mueve, marcha.
        Si está quieta, regresa a su posición original.
        """
        if not is_moving:
            if abs(self.march_angle) > self.return_speed:
                self.march_angle -= math.copysign(self.return_speed, self.march_angle)
            else:
                self.march_angle = 0
            return
        
        self.march_angle += self.march_speed * self.march_direction
        
        if abs(self.march_angle) > self.march_max_angle:
            self.march_direction *= -1

    def draw(self, position_offset, invert_swing=False):
        """
        Dibuja la pata. La rotación es sobre el eje X para
        levantarla (como una marcha).
        """
        if not self.obj:
            return
            
        glPushMatrix()
        
        angle_to_use = -self.march_angle if invert_swing else self.march_angle
        angle_rad = math.radians(angle_to_use)
        
        tx, ty, tz = position_offset
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        pata_matrix = [
            1.0,   0.0,    0.0,   0.0,
            0.0, cos_a,  sin_a,   0.0,
            0.0, -sin_a,  cos_a,  0.0,
             tx,    ty,     tz,   1.0
        ]
        
        glMultMatrixf(pata_matrix)
        self.obj.render()
        glPopMatrix()


class Gallina:
    """
    Clase principal de la gallina. Gestiona el estado general, movimiento,
    y contiene las instancias de las patas y alas.
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
        
        self.speed = 0.5
        self.turn_speed = 1.5
        
        self.base_height = 6.5      
        
        self.pata_izq = Pata(filepath="obj/gallina/pataizq.obj")
        self.pata_der = Pata(filepath="obj/gallina/patader.obj")
        self.ala_izq = Ala(filepath="obj/gallina/alaizq.obj")
        self.ala_der = Ala(filepath="obj/gallina/alader.obj")
        
        pata_x = 0.24
        pata_y = -0.35 
        pata_z = 0.0
        self.offset_pata_izq = [pata_x, pata_y, pata_z]
        self.offset_pata_der = [-pata_x, pata_y, pata_z]

        ala_x = 0.42
        ala_y = 0.3
        ala_z = -0.31
        self.offset_ala_izq = [ala_x, ala_y, ala_z]
        self.offset_ala_der = [-ala_x, ala_y, ala_z]


    def move(self, keys):
        """
        Procesa la entrada del teclado para actualizar el estado de la gallina.
        """
        is_moving = False

        if keys[pygame.K_LEFT]:
            self.rotation_y += self.turn_speed
        if keys[pygame.K_RIGHT]:
            self.rotation_y -= self.turn_speed
            
        rad = math.radians(self.rotation_y)
        dir_x = math.cos(rad)
        dir_z = -math.sin(rad)
        
        if keys[pygame.K_UP]:
            self.position[0] += dir_x * self.speed
            self.position[2] += dir_z * self.speed
            is_moving = True
        if keys[pygame.K_DOWN]:
            self.position[0] -= dir_x * self.speed
            self.position[2] -= dir_z * self.speed
            is_moving = True
        
        self.pata_izq.update(is_moving)
        self.pata_der.update(is_moving)
        self.ala_izq.update(is_moving)
        self.ala_der.update(is_moving)

    def draw(self):
        """
        Dibuja el cuerpo de la gallina y luego a sus partes hijas.
        """
        if not self.obj:
            return
            
        glPushMatrix()
        
        tx, ty, tz = self.position
        ty += self.base_height 
        sx = sy = sz = self.scale_factor
        r = math.radians(self.rotation_y)
        s = math.radians(-90.0) # Ajuste de orientación

        cos_r, sin_r = math.cos(r), math.sin(r)
        cos_s, sin_s = math.cos(s), math.sin(s)

        m0 = sx * (cos_r * cos_s - sin_r * sin_s)
        m2 = sx * (-cos_r * sin_s - sin_r * cos_s)
        m5 = sy
        m8 = sz * (sin_r * cos_s + cos_r * sin_s)
        m10 = sz * (-sin_r * sin_s + cos_r * cos_s)

        gallina_matrix = [
            m0,  0.0,  m2,  0.0,
           0.0,   m5, 0.0,  0.0,
            m8,  0.0, m10,  0.0,
            tx,   ty,  tz,  1.0
        ]
        
        glMultMatrixf(gallina_matrix)
        
        self.obj.render()
        
        self.pata_izq.draw(self.offset_pata_izq, invert_swing=False)
        self.pata_der.draw(self.offset_pata_der, invert_swing=True)
        
        self.ala_izq.draw(self.offset_ala_izq, invert_sweep=False)
        self.ala_der.draw(self.offset_ala_der, invert_sweep=True)
        
        glPopMatrix()