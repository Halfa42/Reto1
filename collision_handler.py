import math

class CircularObstacle:
    """Representa un obstáculo circular (árbol, objeto, etc.)"""
    def __init__(self, x, z, radius):
        self.x = x
        self.z = z
        self.radius = radius

class RectangularObstacle:
    """Representa un obstáculo rectangular (edificios, estructuras)"""
    def __init__(self, vertices):
        self.vertices = vertices  # Lista de 4 tuplas (x, z) formando un rectángulo
        # Calcular bounding box
        xs = [v[0] for v in vertices]
        zs = [v[1] for v in vertices]
        self.min_x = min(xs)
        self.max_x = max(xs)
        self.min_z = min(zs)
        self.max_z = max(zs)

class CollisionHandler:
    """Maneja todas las colisiones del juego"""
    
    SCALE = 7.0
    TREE_RADIUS = 1.5  # Radio reducido para árboles (antes era 14.0)
    SMALL_OBJECT_RADIUS = 1.5  # Radio para objetos pequeños
    
    def __init__(self):
        # Lista de obstáculos circulares (árboles)
        tree_coords = [
            (12.393, 13.74), (14.078, 10.474), (6.3949, 10.571),
            (-13.1796, -5.71744), (-14.1795, -10.081), (-12.7376, -13.1353),
            (-9.12857, -15.5624), (-5.38219, -14.1682), (-2.95916, -13.0208),
            (-0.020705, -13.9497), (8.74049, -2.58273), (12.1852, -14.8262),
            (2.31538, -14.1933), (7.64738, -15.4393), (6.23518, -12.692),
            (9.37471, -12.9266), (2.0096, -10.4211), (7.03635, -7.36681),
            (10.7497, -10.6635), (14.3611, -9.92402), (9.75964, -6.10734),
            (13.3382, -4.24951)
        ]
        
        # Otros objetos pequeños
        small_objects = [(3.6358, -7.0076), (-2.3142, -6.9642)]
        
        # Crear obstáculos circulares escalados
        self.obstacles = []
        
        # Agregar árboles
        for x, z in tree_coords:
            self.obstacles.append(
                CircularObstacle(x * self.SCALE, z * self.SCALE, self.TREE_RADIUS)
            )
        
        # Agregar objetos pequeños
        for x, z in small_objects:
            self.obstacles.append(
                CircularObstacle(x * self.SCALE, z * self.SCALE, self.SMALL_OBJECT_RADIUS)
            )
        
        # Obstáculos rectangulares (edificios y estructuras)
        rectangular_coords = [
            # Lago (primer rectángulo)
            [(13.11, 8.485), (3.863, 8.485), (3.863, -0.7709), (13.11, -0.7709)],
            # Estructuras
            [(-3.857, -5.4), (-10.03, -5.4), (-10.03, -13.11), (-3.857, -13.11)],
            [(-0.773, 16.2), (-16.2, 16.2), (-16.2, 5.402), (-0.773, 5.402)],
            [(-3.857, 5.4), (-14.65, 5.4), (-14.65, 3.857), (-3.857, 3.857)],
            [(-5.4, 3.857), (-14.65, 3.857), (-14.65, 2.312), (-5.4, 2.312)],
            [(-6.942, 2.312), (-14.65, 2.312), (-14.65, -0.772), (-6.942, -0.772)],
            [(-8.485, -0.772), (-13.1, -0.772), (-13.1, -2.315), (-8.485, -2.315)]
        ]
        
        # Crear obstáculos rectangulares escalados
        self.rectangular_obstacles = []
        for rect_coords in rectangular_coords:
            scaled_coords = [(x * self.SCALE, z * self.SCALE) for x, z in rect_coords]
            self.rectangular_obstacles.append(RectangularObstacle(scaled_coords))
    
    def point_in_polygon(self, x, z, vertices):
        """
        Verifica si un punto (x, z) está dentro de un polígono
        usando el algoritmo Ray Casting
        """
        n = len(vertices)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, zi = vertices[i]
            xj, zj = vertices[j]
            
            if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / (zj - zi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def check_circular_collision(self, x, z, entity_radius=0):
        """
        Verifica colisión con obstáculos circulares
        entity_radius: radio adicional de la entidad que se está moviendo
        """
        for obstacle in self.obstacles:
            distance = math.sqrt((x - obstacle.x)**2 + (z - obstacle.z)**2)
            if distance < (obstacle.radius + entity_radius):
                return True
        return False
    
    def check_rectangular_collision(self, x, z, entity_radius=0):
        """
        Verifica colisión con obstáculos rectangulares
        Usa bounding box expandido por el radio de la entidad
        """
        for rect in self.rectangular_obstacles:
            # Bounding box expandido
            if (x + entity_radius > rect.min_x and 
                x - entity_radius < rect.max_x and
                z + entity_radius > rect.min_z and 
                z - entity_radius < rect.max_z):
                
                # Verificación más precisa: punto dentro del polígono
                if self.point_in_polygon(x, z, rect.vertices):
                    return True
                
                # Verificar si el círculo de la entidad intersecta con el rectángulo
                # Encontrar el punto más cercano del rectángulo al círculo
                closest_x = max(rect.min_x, min(x, rect.max_x))
                closest_z = max(rect.min_z, min(z, rect.max_z))
                
                # Calcular distancia del círculo al punto más cercano
                distance = math.sqrt((x - closest_x)**2 + (z - closest_z)**2)
                
                if distance < entity_radius:
                    return True
        
        return False
    
    def is_valid_position(self, x, z, entity_radius=4.0):
        """
        Verifica si una posición es válida (sin colisiones)
        
        Args:
            x, z: Coordenadas en OpenGL
            entity_radius: Radio de colisión de la entidad (robot=4.0, gallina=3.0)
        
        Returns:
            bool: True si la posición es válida, False si hay colisión
        """
        # Verificar colisión con obstáculos rectangulares
        if self.check_rectangular_collision(x, z, entity_radius):
            return False
        
        # Verificar colisión con obstáculos circulares
        if self.check_circular_collision(x, z, entity_radius):
            return False
        
        return True
    
    def get_valid_position(self, old_x, old_z, new_x, new_z, entity_radius=8.0):
        """
        Intenta encontrar una posición válida cercana a la deseada
        Si la posición nueva tiene colisión, devuelve la posición antigua
        
        Args:
            old_x, old_z: Posición actual
            new_x, new_z: Posición deseada
            entity_radius: Radio de colisión de la entidad
        
        Returns:
            tuple: (x, z) posición válida
        """
        # Si la nueva posición es válida, usarla
        if self.is_valid_position(new_x, new_z, entity_radius):
            return new_x, new_z
        
        # Si no es válida, intentar movimiento solo en X
        if self.is_valid_position(new_x, old_z, entity_radius):
            return new_x, old_z
        
        # Si no es válida, intentar movimiento solo en Z
        if self.is_valid_position(old_x, new_z, entity_radius):
            return old_x, new_z
        
        # Si ninguna funciona, quedarse en la posición actual
        return old_x, old_z
    
    def add_circular_obstacle(self, x, z, radius=None):
        """Agrega un nuevo obstáculo circular"""
        if radius is None:
            radius = self.TREE_RADIUS
        self.obstacles.append(CircularObstacle(x, z, radius))
    
    def add_rectangular_obstacle(self, vertices):
        """Agrega un nuevo obstáculo rectangular
        vertices: lista de 4 tuplas (x, z)
        """
        self.rectangular_obstacles.append(RectangularObstacle(vertices))
    
    def get_obstacles_info(self):
        """Retorna información de los obstáculos para debug/visualización"""
        return {
            'circular_obstacles': [(obs.x, obs.z, obs.radius) for obs in self.obstacles],
            'rectangular_obstacles': [rect.vertices for rect in self.rectangular_obstacles]
        }