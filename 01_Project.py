from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time
import numpy as np


# Camera and application state variables
camera_mode = 'free'  # 'free' or 'planet'
camera_pos = [0, 500, 500]
camera_target = [0, 0, 0]
orbit_center = [0, 0, 0]
orbit_radius = 300
orbit_angle = 0
zoom_speed = 5
is_paused = False
show_orbit_paths = True
start_time = time.time()

# Lighting parameters
sun_brightness = 1.0
sun_color = [1.0, 1.0, 0.8]
sun_x = 100
sun_y = 30
sun_z = 30

# Window size
width, height = 1000, 800

NUM_STARS = 2000
STAR_FIELD_RADIUS = 1500

stars = []
for _ in range(NUM_STARS):
    x = random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS)
    y = random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS)
    z = random.uniform(-STAR_FIELD_RADIUS, STAR_FIELD_RADIUS)
    stars.append((x,y,z))

# Planet data structure
class Planet:
    def __init__(self, name, color, orbit_radius, size, orbit_speed, orbit_period):
        self.name = name
        self.color = color
        self.orbit_radius = orbit_radius
        self.size = size
        self.orbit_speed = orbit_speed
        self.orbit_period = orbit_period
        self.angle = random.uniform(0, 2*math.pi)
        self.position = [0, 0, 0]
        self.removed = False
        # Blasting / remove timer
        self.blasting = False
        self.blast_start_time = None
        self.is_temp = False
        self.moving = True

    def update_position(self, delta_time):
        if not self.removed and self.moving:
            self.angle += self.orbit_speed * delta_time
            self.position[0] = self.orbit_radius * math.cos(self.angle)
            self.position[1] = 0
            self.position[2] = self.orbit_radius * math.sin(self.angle)

# Replace the planets initialization with more realistic colors
speed = 10000
earth_orbit_speed = 2 * math.pi / speed  # ≈0.000628 (1 orbit in 10,000 units of time)

planets = [
    Planet('Mercury', (0.5, 0.5, 0.5), 200, 8, earth_orbit_speed * (1/0.24), 0),
    Planet('Venus', (0.9, 0.8, 0.6), 240, 12, earth_orbit_speed * (1/0.62), math.pi/4),
    Planet('Earth', (0.2, 0.6, 0.8), 280, 14, earth_orbit_speed, math.pi/2),
    Planet('Mars', (0.8, 0.3, 0.2), 320, 11, earth_orbit_speed * (1/1.88), math.pi),
    Planet('Jupiter', (0.9, 0.6, 0.3), 400, 35, earth_orbit_speed * (1/11.86), 3*math.pi/2),
    Planet('Saturn', (0.9, 0.8, 0.5), 480, 30, earth_orbit_speed * (1/29.45), math.pi/6),
    Planet('Uranus', (0.3, 0.8, 0.7), 550, 22, earth_orbit_speed * (1/84.02), 5*math.pi/6),
    Planet('Neptune', (0.2, 0.4, 0.9), 610, 21, earth_orbit_speed * (1/164.79), 4*math.pi/3)
]

def draw_stars():
    global start_time
    current_time = time.time() - start_time
    glPointSize(2.0)
    glBegin(GL_POINTS)
    current_time = current_time / 1000.0  # slow time for twinkle effect
    for i, (x, y, z) in enumerate(stars):
        intensity = 0.5 + 0.5 * math.sin(current_time * 5 + i)
        glColor3f(intensity, intensity, intensity)
        glVertex3f(x, y, z)
    glEnd()

# Selected planet for info display
selected_planet = None

# Utility functions
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_planet(planet, position):
    elapsed = (time.time() - planet.blast_start_time) if planet.blast_start_time else 0
    glPushMatrix()
    glTranslatef(position[0], position[1], position[2])
    if planet.blasting:
        elapsed = (elapsed - planet.blast_start_time) / 1000.0
        blast_size = planet.size + 12 * math.sin(elapsed * 10)
        glColor3f(1, 0.5, 0)  # Orange blast
        gluSphere(gluNewQuadric(),planet.size+10, 20, 20)
    else:
        glColor3f(*planet.color)
        gluSphere(gluNewQuadric(),planet.size, 20, 20)
    glPopMatrix()

def draw_orbit(planet):
    if show_orbit_paths:
        glColor3f(1,1,1)
        glBegin(GL_LINE_LOOP)
        for i in range(60):
            theta = 2 * math.pi * i / 60
            x = planet.orbit_radius * math.cos(theta)
            z = planet.orbit_radius * math.sin(theta)
            glVertex3f(x, 0, z)
        glEnd()
        
# Adding a random planet with a random orbit
def add_random_planet(orbit_radius):
    color = (random.random(), random.random(), random.random())
    size = random.randint(8, 30)
    orbit_speed = random.uniform(0.005, 0.015)
    angle = random.uniform(0, 2*math.pi)
    new_planet = Planet('Random', color, orbit_radius, size, orbit_speed, angle)
    new_planet.is_temp = True
    planets.append(new_planet)

# Collision checking
def check_collision(p1, p2):
    dx = p1.position[0] - p2.position[0]
    dy = p1.position[1] - p2.position[1]
    dz = p1.position[2] - p2.position[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    return dist < (p1.size + p2.size)

def draw_controls_legend():
    legend_lines = [
        "Controls:",
        "'p' - Toggle camera mode",
        "'o' - Toggle orbit paths",
        "'r' - Reset planets",
        "'c' - Pause/Resume",
        "'a' - Add random planet",
        "+/- - Inc/Dec orbit radius",
        "s/x - Inc/Dec planet size",
        "m/n - Inc/Dec orbit speed",
        "l/k - Inc/Dex sun size",
        "Click planet - Select planet"
    ]
    x = width - 250  # Right corner X (adjust 250 as per max text width)
    y_start = height - 20
    line_height = 20
    glColor3f(1.0, 1.0, 1.0)  # White color
    
    for i, line in enumerate(legend_lines):
        draw_text(x, y_start - i * line_height, line)


def draw_scene():
    global sun_x,sun_y,sun_z
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    draw_stars()
    # Setup camera
    if camera_mode == 'free':
        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2], 0,0,0, 0,1,0)
    elif camera_mode == 'orbit' and selected_planet:
        target_pos = selected_planet.position
        cam_x = target_pos[0] + orbit_radius * math.cos(orbit_angle)
        cam_z = target_pos[2] + orbit_radius * math.sin(orbit_angle)
        gluLookAt(cam_x, target_pos[1] + 50, cam_z, target_pos[0], target_pos[1], target_pos[2], 0,1,0)
    else:
        gluLookAt(0, 500, 500, 0,0,0, 0,1,0)


    # Draw Sun
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(0,0,0)
    glutSolidSphere(sun_x, sun_y, sun_z) 
    glPopMatrix()

    # Draw planets and orbits
    for planet in planets:
        if not planet.removed:
            planet.update_position(1)
            draw_orbit(planet)
            draw_planet(planet, planet.position)

    # Collision and blast logic
    current_time = time.time()

    for i, p1 in enumerate(planets):
        for j, p2 in enumerate(planets):
            if i >= j or p1.removed or p2.removed:
                continue
            if check_collision(p1, p2):
                if not p1.blasting and not p2.blasting:
                    p1.blasting, p2.blasting = True, True
                    p1.blast_start_time = p2.blast_start_time = current_time
                    p1.moving = False
                    p2.moving = False

    # Remove blasted planets after 3 seconds
    for planet in planets:
        if planet.blasting and planet.blast_start_time:
            if current_time - planet.blast_start_time > 3:
                planet.removed = True
    planets[:] = [p for p in planets if not p.removed]

    # Draw info panel
    if selected_planet:
        info_x, info_y = 10, 50
        draw_text(info_x, info_y, f"Selected: {selected_planet.name}")
        dist = math.sqrt(sum([c**2 for c in selected_planet.position]))
        draw_text(info_x, info_y + 20, f"Distance from Sun: {dist:.1f}")
        draw_text(info_x, info_y + 40, f"Size: {selected_planet.size}")
        draw_text(info_x, info_y + 60, f"Orbit Period: {selected_planet.orbit_period} days")
    else:
        draw_text(10, 50, "No planet selected")
    
    draw_controls_legend()
    glutSwapBuffers()

def idle():
    global orbit_angle
    if not is_paused:
        if camera_mode == 'orbit':
            orbit_angle += 0.01
        glutPostRedisplay()



def keyboard(key, x, y):
    global camera_mode, camera_pos, selected_planet, show_orbit_paths, is_paused, planets, speed, earth_orbit_speed, sun_x, sun_y, sun_z
    key = key.decode('utf-8')
    if key == 'p':
        if camera_mode == 'free':
            camera_mode = 'orbit'
        else:
            camera_mode = 'free'
    elif key == 'o':
        show_orbit_paths = not show_orbit_paths
    elif key == 'r':
        speed = 10000
        earth_orbit_speed = 2 * math.pi / speed
        planets = [
            Planet('Mercury', (0.5, 0.5, 0.5), 200, 8, earth_orbit_speed * (1/0.24), 0),
            Planet('Venus', (0.9, 0.8, 0.6), 240, 12, earth_orbit_speed * (1/0.62), math.pi/4),
            Planet('Earth', (0.2, 0.6, 0.8), 280, 14, earth_orbit_speed, math.pi/2),
            Planet('Mars', (0.8, 0.3, 0.2), 320, 11, earth_orbit_speed * (1/1.88), math.pi),
            Planet('Jupiter', (0.9, 0.6, 0.3), 400, 35, earth_orbit_speed * (1/11.86), 3*math.pi/2),
            Planet('Saturn', (0.9, 0.8, 0.5), 480, 30, earth_orbit_speed * (1/29.45), math.pi/6),
            Planet('Uranus', (0.3, 0.8, 0.7), 550, 22, earth_orbit_speed * (1/84.02), 5*math.pi/6),
            Planet('Neptune', (0.2, 0.4, 0.9), 610, 21, earth_orbit_speed * (1/164.79), 4*math.pi/3)
        ]
        planets = [p for p in planets if not getattr(p, 'is_temp', False)]
        selected_planet = None
        for p in planets:
            p.removed = False
            p.blasting = False
            p.blast_start_time = None
            p.moving = True
            p.is_temp = False
    elif key == 'a':
        add_random_planet(random.choice([250, 300, 350, 380, 420, 500, 530, 580]))
        glutPostRedisplay()
    elif key == 'c':
        is_paused = not is_paused
    elif key == '+':
        if selected_planet:
            selected_planet.orbit_radius += 10
    elif key == '-':
        if selected_planet:
            selected_planet.orbit_radius = max(10, selected_planet.orbit_radius - 10)
    elif key == 's':
        if selected_planet:
            selected_planet.size += 1
    elif key == 'x':
        if selected_planet:
            selected_planet.size = max(1, selected_planet.size - 1)
    elif key == 'l':
        sun_x +=1
        sun_y +=1
        sun_z +=1
    elif key == 'k':
        sun_x -=1
        sun_y -=1
        sun_z -=1            
    elif key == 'm':
        speed = max(1000, speed - 1000)  # prevent speed <= 0
        earth_orbit_speed = 2 * math.pi / speed
        for p in planets:
            if p.name == 'Mercury':
                p.orbit_speed = earth_orbit_speed * (1/0.24)
            elif p.name == 'Venus':
                p.orbit_speed = earth_orbit_speed * (1/0.62)
            elif p.name == 'Earth':
                p.orbit_speed = earth_orbit_speed
            elif p.name == 'Mars':
                p.orbit_speed = earth_orbit_speed * (1/1.88)
            elif p.name == 'Jupiter':
                p.orbit_speed = earth_orbit_speed * (1/11.86)
            elif p.name == 'Saturn':
                p.orbit_speed = earth_orbit_speed * (1/29.45)
            elif p.name == 'Uranus':
                p.orbit_speed = earth_orbit_speed * (1/84.02)
            elif p.name == 'Neptune':
                p.orbit_speed = earth_orbit_speed * (1/164.79)
    elif key == 'n':
        speed += 1000
        earth_orbit_speed = 2 * math.pi / speed
        for p in planets:
            if p.name == 'Mercury':
                p.orbit_speed = earth_orbit_speed * (1/0.24)
            elif p.name == 'Venus':
                p.orbit_speed = earth_orbit_speed * (1/0.62)
            elif p.name == 'Earth':
                p.orbit_speed = earth_orbit_speed
            elif p.name == 'Mars':
                p.orbit_speed = earth_orbit_speed * (1/1.88)
            elif p.name == 'Jupiter':
                p.orbit_speed = earth_orbit_speed * (1/11.86)
            elif p.name == 'Saturn':
                p.orbit_speed = earth_orbit_speed * (1/29.45)
            elif p.name == 'Uranus':
                p.orbit_speed = earth_orbit_speed * (1/84.02)
            elif p.name == 'Neptune':
                p.orbit_speed = earth_orbit_speed * (1/164.79)
    glutPostRedisplay()

def special_keys(key, x, y):
    global camera_pos, camera_mode
    if key == GLUT_KEY_LEFT:
        if camera_mode == 'free':
            camera_pos[0] -= 10
    elif key == GLUT_KEY_RIGHT:
        if camera_mode == 'free':
            camera_pos[0] += 10
    elif key == GLUT_KEY_UP:
        camera_pos[1] += 10
    elif key == GLUT_KEY_DOWN:
        camera_pos[1] -= 10
    glutPostRedisplay()

# Helper math for ray casting picking

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

def get_ray_from_mouse(x, y, width, height, fovY, camera_pos):
    aspect = width / height
    fov_rad = math.radians(fovY)

    # Normalized device coordinates
    ndc_x = (2.0 * x) / width - 1.0
    ndc_y = 1.0 - (2.0 * y) / height  # flip Y

    cam_pos_np = np.array(camera_pos)
    target = np.array([0, 0, 0])
    up = np.array([0, 1, 0])

    forward = normalize(target - cam_pos_np)
    right = normalize(np.cross(forward, up))
    cam_up = np.cross(right, forward)

    near_plane_height = 2.0 * math.tan(fov_rad / 2.0)
    near_plane_width = near_plane_height * aspect

    point = cam_pos_np + forward
    point += right * ndc_x * (near_plane_width / 2.0)
    point += cam_up * ndc_y * (near_plane_height / 2.0)

    ray_dir = normalize(point - cam_pos_np)
    return cam_pos_np, ray_dir

def ray_sphere_intersect(ray_origin, ray_dir, sphere_center, sphere_radius):
    L = sphere_center - ray_origin
    t_ca = np.dot(L, ray_dir)
    if t_ca < 0:
        return False, None
    d2 = np.dot(L, L) - t_ca * t_ca
    if d2 > sphere_radius * sphere_radius:
        return False, None
    t_hc = math.sqrt(sphere_radius * sphere_radius - d2)
    t0 = t_ca - t_hc
    t1 = t_ca + t_hc
    dist = t0 if t0 > 0 else t1
    return True, dist 

def mouse_click(button, state, x, y):
    global selected_planet
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        ray_origin, ray_dir = get_ray_from_mouse(x, y, width, height, 60, camera_pos)
        min_dist = float('inf')
        clicked_planet = None
        for planet in planets:
            if planet.removed:
                continue
            center = np.array(planet.position)
            radius = planet.size
            hit, dist = ray_sphere_intersect(ray_origin, ray_dir, center, radius)
            if hit and dist < min_dist:
                min_dist = dist
                clicked_planet = planet
        selected_planet = clicked_planet
        glutPostRedisplay()
