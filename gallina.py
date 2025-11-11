import pygame
from OpenGL.GL import *
import math

from objloader import OBJ

class Ala:
    def __init__(self, filepath):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except:
            self.obj = None
        self.flap_phase = 0.0
        self.flap_direction = 1
        self.flap_speed = 3.0
        self.flap_max_angle = 30.0

    def update(self, is_moving):
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
        if not self.obj:
            return
        glPushMatrix()
        tx, ty, tz = position_offset
        angle_x_flap = abs(self.flap_phase)
        angle_y_sweep_amount = abs(self.flap_phase) * 0.5
        angle_y_sweep = angle_y_sweep_amount if invert_sweep else -angle_y_sweep_amount
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
        ala_matrix = [m0, 0.0, m2, 0.0, m4, m5, m6, 0.0, m8, m9, m10, 0.0, tx, ty, tz, 1.0]
        glMultMatrixf(ala_matrix)
        self.obj.render()
        glPopMatrix()

class Pata:
    def __init__(self, filepath):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except:
            self.obj = None
        self.march_angle = 0.0
        self.march_direction = 1
        self.march_speed = 4.0
        self.march_max_angle = 20.0
        self.return_speed = 6.0

    def update(self, is_moving):
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
        if not self.obj:
            return
        glPushMatrix()
        angle_to_use = -self.march_angle if invert_swing else self.march_angle
        angle_rad = math.radians(angle_to_use)
        tx, ty, tz = position_offset
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        pata_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, cos_a, sin_a, 0.0, 0.0, -sin_a, cos_a, 0.0, tx, ty, tz, 1.0]
        glMultMatrixf(pata_matrix)
        self.obj.render()
        glPopMatrix()

class Gallina:
    WALK_INTERPOLATION_SPEED = 0.5  
    FLEE_INTERPOLATION_SPEED = 1.0
    WALK_ANIMATION_SPEED = 4.0      
    FLEE_ANIMATION_SPEED = 8.0
    
    def __init__(self, filepath, initial_pos, scale):
        try:
            self.obj = OBJ(filepath, swapyz=True)
        except:
            self.obj = None
        self.position = list(initial_pos)
        self.scale_factor = scale
        self.rotation_y = 0.0
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
        self.target_position = list(initial_pos)
        self.previous_position = list(initial_pos)
        self.movement_speed = self.WALK_INTERPOLATION_SPEED
        self.is_moving = False
        self.target_rotation_y = 0.0
        self.rotation_y = 0.0
        self.pata_izq.march_speed = self.WALK_ANIMATION_SPEED
        self.pata_der.march_speed = self.WALK_ANIMATION_SPEED
        self.ala_izq.flap_speed = self.WALK_ANIMATION_SPEED / 1.3 
        self.ala_der.flap_speed = self.WALK_ANIMATION_SPEED / 1.3
        
    def set_speed_mode(self, mode):
        if mode == "fleeing":
            self.movement_speed = self.FLEE_INTERPOLATION_SPEED
            self.pata_izq.march_speed = self.FLEE_ANIMATION_SPEED
            self.pata_der.march_speed = self.FLEE_ANIMATION_SPEED
            self.ala_izq.flap_speed = self.FLEE_ANIMATION_SPEED / 1.3
            self.ala_der.flap_speed = self.FLEE_ANIMATION_SPEED / 1.3
        else:
            self.movement_speed = self.WALK_INTERPOLATION_SPEED
            self.pata_izq.march_speed = self.WALK_ANIMATION_SPEED
            self.pata_der.march_speed = self.WALK_ANIMATION_SPEED
            self.ala_izq.flap_speed = self.WALK_ANIMATION_SPEED / 1.3
            self.ala_der.flap_speed = self.WALK_ANIMATION_SPEED / 1.3

    def update_from_julia(self, new_x, new_z):
        new_pos = [new_x, 0.0, new_z]
        if new_pos != self.target_position:
            self.previous_position = list(self.position)
            self.target_position = new_pos
            self.is_moving = True
            dx = self.target_position[0] - self.position[0]
            dz = self.target_position[2] - self.position[2]
            if abs(dx) > 0.1 or abs(dz) > 0.1:
                angle = math.degrees(math.atan2(-dz, dx))
                self.target_rotation_y = angle

    def animate_step(self):
        if self.is_moving:
            current_x, _, current_z = self.position
            target_x, _, target_z = self.target_position
            dx = target_x - current_x
            dz = target_z - current_z
            distance = math.sqrt(dx**2 + dz**2)
            
            if distance > self.movement_speed:
                self.position[0] += dx * (self.movement_speed / distance)
                self.position[2] += dz * (self.movement_speed / distance)
            else:
                self.position[0] = target_x
                self.position[2] = target_z
                self.is_moving = False
                
            self.pata_izq.update(True)
            self.pata_der.update(True)
            self.ala_izq.update(True)
            self.ala_der.update(True)
            
            if abs(self.rotation_y - self.target_rotation_y) > 1.5:
                diff = self.target_rotation_y - self.rotation_y
                if diff > 180: diff -= 360
                if diff < -180: diff += 360
                self.rotation_y += math.copysign(1.5, diff)
            else:
                self.rotation_y = self.target_rotation_y
        else:
            self.pata_izq.update(False)
            self.pata_der.update(False)
            self.ala_izq.update(False)
            self.ala_der.update(False)

    def draw(self):
        if not self.obj:
            return
        glPushMatrix()
        tx, ty, tz = self.position
        ty += self.base_height 
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
        gallina_matrix = [m0, 0.0, m2, 0.0, 0.0, m5, 0.0, 0.0, m8, 0.0, m10, 0.0, tx, ty, tz, 1.0]
        glMultMatrixf(gallina_matrix)
        self.obj.render()
        self.pata_izq.draw(self.offset_pata_izq, invert_swing=False)
        self.pata_der.draw(self.offset_pata_der, invert_swing=True)
        self.ala_izq.draw(self.offset_ala_izq, invert_sweep=False)
        self.ala_der.draw(self.offset_ala_der, invert_sweep=True)
        glPopMatrix()