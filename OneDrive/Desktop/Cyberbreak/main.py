
import pygame
import math
from collections import deque

pygame.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CYBERBREAK: AI CITY - FINAL BATTLE")

clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 16)
big_font = pygame.font.SysFont("Arial", 32)

WHITE = (240, 240, 240)
BLACK = (10, 12, 25)
GREEN = (0, 255, 150)
BLUE = (40, 150, 255)
RED = (255, 65, 75)
YELLOW = (255, 220, 70)
PURPLE = (180, 100, 255)
GREY = (80, 90, 110)
CYAN = (0, 220, 255)
ORANGE = (255, 130, 40)

player = pygame.Rect(70, 70, 30, 30)
player_speed = 4
player_health = 100
player_energy = 100

xp = 0
credits = 0

inventory = []

items = [
    {"name": "access_card", "rect": pygame.Rect(120, 300, 20, 20)},
    {"name": "energy_pack", "rect": pygame.Rect(350, 150, 20, 20)},
    {"name": "energy_pack", "rect": pygame.Rect(820, 250, 20, 20)},
    {"name": "data_chip", "rect": pygame.Rect(720, 540, 20, 20)},
    {"name": "data_chip", "rect": pygame.Rect(220, 500, 20, 20)}
]

terminals = {
    "T1": pygame.Rect(180, 80, 45, 45),
    "T2": pygame.Rect(450, 80, 45, 45),
    "T3": pygame.Rect(750, 80, 45, 45),
    "T4": pygame.Rect(450, 570, 45, 45),
    "T5": pygame.Rect(850, 550, 45, 45)
}

walls = [
    pygame.Rect(280, 180, 180, 30),
    pygame.Rect(550, 180, 180, 30),
    pygame.Rect(150, 400, 180, 30),
    pygame.Rect(520, 400, 180, 30),
    pygame.Rect(780, 350, 30, 130)
]

restricted_area_open = False
gate_mission_completed = False

terminal_open = False
current_terminal = ""
code_input = ""
feedback = ""

inventory_open = False
show_help = False
running = True

boss_unlocked = False
game_won = False

emp_until = 0
shield_until = 0
speed_until = 0

emp_cooldown = 0
shield_cooldown = 0
speed_cooldown = 0

attack_cooldown = 0
projectiles = []


def draw_text(text, x, y, color=WHITE, selected_font=font):
    image = selected_font.render(str(text), True, color)
    screen.blit(image, (x, y))


def distance_between(a, b):
    return math.hypot(a.centerx - b.centerx, a.centery - b.centery)


def get_grid_position(x, y):
    return (x // 40, y // 40)


def find_path(start, goal):
    start = get_grid_position(start[0], start[1])
    goal = get_grid_position(goal[0], goal[1])

    queue = deque([start])
    previous = {start: None}

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    while queue:
        current = queue.popleft()

        if current == goal:
            break

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)

            px = neighbor[0] * 40 + 20
            py = neighbor[1] * 40 + 20

            if px < 20 or px > WIDTH - 20:
                continue

            if py < 20 or py > HEIGHT - 20:
                continue

            test_rect = pygame.Rect(px - 12, py - 12, 24, 24)

            blocked = any(test_rect.colliderect(wall) for wall in walls)

            if neighbor not in previous and not blocked:
                previous[neighbor] = current
                queue.append(neighbor)

    if goal not in previous:
        return []

    path = []
    current = goal

    while current is not None:
        path.append((current[0] * 40 + 20, current[1] * 40 + 20))
        current = previous[current]

    path.reverse()
    return path


class SecurityRobot:

    def __init__(self, x, y, robot_name, robot_config):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.name = robot_name
        self.config = robot_config
        self.health = robot_config["health"]
        self.speed = robot_config["speed"]
        self.detection_range = robot_config["detection_range"]
        self.mode = robot_config["mode"]
        self.path = []
        self.path_index = 0
        self.last_path_update = 0
        self.disabled_until = 0
        self.patrol_direction = 1
        self.start_x = x

    def update(self, player_rect, current_time, shield_active):

        if current_time < self.disabled_until:
            self.mode = "STUNNED"
            return False

        if current_time - self.last_path_update > 700:
            self.last_path_update = current_time

            if distance_between(self.rect, player_rect) < self.detection_range:
                self.mode = "CHASE"
                self.path = find_path(self.rect.center, player_rect.center)
                self.path_index = 1
            else:
                self.mode = "PATROL"

        if self.mode == "CHASE" and self.path:
            if self.path_index < len(self.path):
                target_x, target_y = self.path[self.path_index]

                dx = target_x - self.rect.centerx
                dy = target_y - self.rect.centery
                distance = math.hypot(dx, dy)

                if distance < 8:
                    self.path_index += 1
                elif distance > 0:
                    self.rect.x += int((dx / distance) * self.speed)
                    self.rect.y += int((dy / distance) * self.speed)
        else:
            self.rect.x += self.patrol_direction * self.speed

            if self.rect.x > self.start_x + 100:
                self.patrol_direction = -1

            if self.rect.x < self.start_x - 100:
                self.patrol_direction = 1

        if self.rect.colliderect(player_rect) and not shield_active:
            return True

        return False

    def disable(self, current_time):
        self.disabled_until = current_time + 5000
        self.mode = "STUNNED"

    def draw(self):
        if self.mode == "STUNNED":
            color = GREY
        elif self.mode == "CHASE":
            color = RED
        else:
            color = PURPLE

        pygame.draw.rect(screen, color, self.rect)
        draw_text(self.name, self.rect.x - 10, self.rect.y - 22, WHITE, small_font)


class AICore:

    def __init__(self, x, y, config):
        self.rect = pygame.Rect(x, y, 65, 65)
        self.name = config["name"]
        self.health = config["health"]
        self.max_health = config["health"]
        self.speed = config["speed"]
        self.damage = config["damage"]
        self.attack_delay = config["attack_delay"]
        self.last_attack = 0
        self.direction = 1
        self.last_move = 0
        self.alive = True

    def update(self, current_time, player_rect):
        if not self.alive:
            return

        if current_time - self.last_move > 35:
            self.rect.x += self.direction * self.speed

            if self.rect.x > 850:
                self.direction = -1

            if self.rect.x < 700:
                self.direction = 1

            self.last_move = current_time

        if current_time - self.last_attack >= self.attack_delay:
            create_boss_projectile(self.rect.center, player_rect.center)
            self.last_attack = current_time

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)

        if self.health == 0:
            self.alive = False

    def draw(self):
        if not self.alive:
            return

        pygame.draw.rect(screen, PURPLE, self.rect)
        pygame.draw.rect(screen, CYAN, self.rect, 3)

        draw_text("AI CORE", self.rect.x - 3, self.rect.y - 25, CYAN, small_font)

        pygame.draw.rect(screen, RED, (650, 90, 300, 18))
        health_width = int(300 * self.health / self.max_health)
        pygame.draw.rect(screen, GREEN, (650, 90, health_width, 18))

        draw_text("BOSS HP: " + str(self.health), 650, 115, WHITE, small_font)


robot_config = {
    "health": 100,
    "speed": 2,
    "detection_range": 230,
    "mode": "PATROL"
}

robots = [
    SecurityRobot(350, 280, "BOT-01", robot_config),
    SecurityRobot(600, 300, "BOT-02", robot_config),
    SecurityRobot(800, 450, "BOT-03", robot_config)
]

boss_config = {
    "name": "AI CORE",
    "health": 300,
    "speed": 2,
    "damage": 10,
    "attack_delay": 1200
}

boss = AICore(780, 280, boss_config)


def create_boss_projectile(start, target):
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    distance = math.hypot(dx, dy)

    if distance == 0:
        return

    projectile = {
        "rect": pygame.Rect(start[0] - 7, start[1] - 7, 14, 14),
        "dx": (dx / distance) * 5,
        "dy": (dy / distance) * 5,
        "damage": boss.damage
    }

    projectiles.append(projectile)


def use_emp(current_time):
    global emp_until, emp_cooldown

    if current_time >= emp_cooldown:
        emp_until = current_time + 5000
        emp_cooldown = current_time + 8000

        for robot in robots:
            if distance_between(player, robot.rect) < 220:
                robot.disable(current_time)

        if boss_unlocked and distance_between(player, boss.rect) < 220:
            boss.take_damage(20)


def activate_shield(current_time):
    global shield_until, shield_cooldown

    if current_time >= shield_cooldown:
        shield_until = current_time + 5000
        shield_cooldown = current_time + 10000


def activate_speed_boost(current_time):
    global speed_until, speed_cooldown

    if current_time >= speed_cooldown:
        speed_until = current_time + 5000
        speed_cooldown = current_time + 8000


def player_attack(current_time):
    global attack_cooldown

    if not boss_unlocked:
        return

    if current_time < attack_cooldown:
        return

    attack_cooldown = current_time + 500

    if distance_between(player, boss.rect) < 180 and boss.alive:
        boss.take_damage(25)


def open_terminal(terminal_id):
    global terminal_open, current_terminal, code_input, feedback

    terminal_open = True
    current_terminal = terminal_id
    code_input = ""
    feedback = ""


def check_terminal():
    global feedback, xp, credits
    global restricted_area_open, gate_mission_completed
    global boss_unlocked

    answer = code_input.strip().lower()

    if current_terminal == "T1":
        correct = "player_level = 5"

        if answer == correct:
            feedback = "Correct! Variable assigned."
            xp += 50
            credits += 50
        else:
            feedback = "Incorrect. Try again."

    elif current_terminal == "T2":
        correct = 'if robot_status == "offline": access = "granted"'

        if answer == correct:
            feedback = "Robot security bypassed!"
            xp += 75
            credits += 50
        else:
            feedback = "Incorrect. Check your if condition."

    elif current_terminal == "T3":
        correct = "for robot in robot_squad: disable(robot)"

        if answer == correct:
            feedback = "Robot squad disabled!"
            xp += 100
            credits += 75

            for robot in robots:
                robot.disable(pygame.time.get_ticks())
        else:
            feedback = "Incorrect. Think about for loops."

    elif current_terminal == "T4":
        correct = 'if "access_card" in inventory: access = "granted"'

        if answer == correct:
            if "access_card" in inventory:
                restricted_area_open = True
                feedback = "Access granted! Restricted area unlocked."
                xp += 100
                credits += 100
                gate_mission_completed = True
            else:
                feedback = "You need to collect the access card first."
        else:
            feedback = "Incorrect. Check the list membership condition."

    elif current_terminal == "T5":
        correct = 'if ai_config["mode"] == "chase": robot.navigate()'

        if answer == correct:
            if not boss_unlocked:
                feedback = "AI Core detected! Final battle unlocked."
                xp += 150
                credits += 150
                boss_unlocked = True
            else:
                feedback = "AI Core is already activated."
        else:
            feedback = "Incorrect. Check dictionary lookup and method call."


def draw_terminal():
    pygame.draw.rect(screen, (20, 25, 50), (150, 180, 700, 350))
    pygame.draw.rect(screen, CYAN, (150, 180, 700, 350), 3)

    draw_text("SYSTEM TERMINAL: " + current_terminal, 180, 205, CYAN, big_font)

    questions = {
        "T1": [
            "MISSION: Assign a value to a variable.",
            "Write: player_level = 5"
        ],
        "T2": [
            "MISSION: Use an if condition to check robot status.",
            'Write: if robot_status == "offline": access = "granted"'
        ],
        "T3": [
            "MISSION: Use a for loop to disable every robot.",
            "Write: for robot in robot_squad: disable(robot)"
        ],
        "T4": [
            "MISSION: Check whether access_card exists in inventory.",
            'Write: if "access_card" in inventory: access = "granted"'
        ],
        "T5": [
            "MISSION: Use a dictionary and call a robot method.",
            'Write: if ai_config["mode"] == "CHASE": robot.navigate()'
        ]
    }

    draw_text(questions[current_terminal][0], 180, 270, WHITE)
    draw_text(questions[current_terminal][1], 180, 310, GREEN, small_font)

    draw_text("Your code:", 180, 375, YELLOW)
    pygame.draw.rect(screen, BLACK, (180, 405, 640, 40))
    draw_text(code_input, 190, 415, GREEN, small_font)

    draw_text(feedback, 180, 465, YELLOW, small_font)
    draw_text("ENTER = Submit     BACKSPACE = Delete     ESC = Close", 180, 495, WHITE, small_font)


def draw_inventory():
    pygame.draw.rect(screen, (20, 25, 50), (300, 200, 400, 300))
    pygame.draw.rect(screen, GREEN, (300, 200, 400, 300), 2)

    draw_text("PLAYER INVENTORY", 350, 225, GREEN, big_font)

    if not inventory:
        draw_text("Inventory is empty.", 350, 290)
    else:
        for i, item in enumerate(inventory):
            draw_text(item, 350, 280 + i * 30)

    draw_text("H = Use Energy Pack", 350, 420, YELLOW, small_font)
    draw_text("J = Check Access Card", 350, 450, YELLOW, small_font)
    draw_text("I = Close Inventory", 350, 475, WHITE, small_font)


def draw_world():
    screen.fill(BLACK)

    for x in range(0, WIDTH, 50):
        pygame.draw.line(screen, (20, 35, 55), (x, 0), (x, HEIGHT))

    for y in range(0, HEIGHT, 50):
        pygame.draw.line(screen, (20, 35, 55), (0, y), (WIDTH, y))

    for wall in walls:
        pygame.draw.rect(screen, GREY, wall)

    for name, rect in terminals.items():
        color = GREEN if name != "T5" else CYAN
        pygame.draw.rect(screen, color, rect)
        draw_text(name, rect.x + 8, rect.y + 12, BLACK, small_font)

    for item in items:
        pygame.draw.rect(screen, YELLOW, item["rect"])

    if restricted_area_open:
        pygame.draw.rect(screen, GREEN, (900, 550, 40, 100))
        draw_text("UNLOCKED", 870, 525, GREEN, small_font)
    else:
        pygame.draw.rect(screen, RED, (900, 550, 40, 100))
        draw_text("LOCKED", 880, 525, RED, small_font)

    for robot in robots:
        robot.draw()

    if boss_unlocked and boss.alive:
        boss.draw()

    for projectile in projectiles:
        pygame.draw.ellipse(screen, ORANGE, projectile["rect"])

    pygame.draw.rect(screen, BLUE, player)

    if pygame.time.get_ticks() < shield_until:
        pygame.draw.circle(screen, CYAN, player.center, 28, 2)

    pygame.draw.rect(screen, RED, (20, 15, 150, 15))
    pygame.draw.rect(screen, GREEN, (20, 15, max(0, int(player_health * 1.5)), 15))

    pygame.draw.rect(screen, GREY, (190, 15, 150, 15))
    pygame.draw.rect(screen, CYAN, (190, 15, max(0, int(player_energy * 1.5)), 15))

    draw_text("HP", 20, 35, WHITE, small_font)
    draw_text("ENERGY", 190, 35, WHITE, small_font)

    draw_text("XP: " + str(xp), 370, 15, GREEN)
    draw_text("Credits: " + str(credits), 490, 15, YELLOW)

    draw_text("1 EMP  2 SHIELD  3 SPEED  SPACE ATTACK", 20, 660, WHITE, small_font)


def draw_ability_status(current_time):
    emp_text = "READY" if current_time >= emp_cooldown else "WAIT"
    shield_text = "READY" if current_time >= shield_cooldown else "WAIT"
    speed_text = "READY" if current_time >= speed_cooldown else "WAIT"

    draw_text("EMP: " + emp_text, 700, 15, CYAN, small_font)
    draw_text("SHIELD: " + shield_text, 700, 35, GREEN, small_font)
    draw_text("SPEED: " + speed_text, 700, 55, YELLOW, small_font)


def draw_help():
    pygame.draw.rect(screen, (20, 25, 50), (200, 150, 600, 400))
    pygame.draw.rect(screen, CYAN, (200, 150, 600, 400), 2)

    draw_text("CYBERBREAK - CONTROLS", 300, 180, CYAN, big_font)

    instructions = [
        "W A S D / Arrow Keys = Move",
        "E = Open nearby terminal",
        "I = Open inventory",
        "H = Use energy pack",
        "J = Check access card",
        "1 = EMP Blast",
        "2 = Energy Shield",
        "3 = Speed Boost",
        "SPACE = Attack AI Core",
        "F1 = Help",
        "ESC = Close screen"
    ]

    for i, instruction in enumerate(instructions):
        draw_text(instruction, 280, 235 + i * 27, WHITE, small_font)


def draw_victory_screen():
    screen.fill(BLACK)

    draw_text("AI CORE DESTROYED!", 300, 180, GREEN, big_font)
    draw_text("MISSION COMPLETED", 350, 245, CYAN, big_font)

    draw_text("You saved the AI City!", 365, 320, WHITE)
    draw_text("All Python missions completed.", 315, 360, YELLOW)

    draw_text("FINAL XP: " + str(xp), 390, 420, GREEN)
    draw_text("FINAL CREDITS: " + str(credits), 365, 455, YELLOW)

    draw_text("Press ESC to exit the game.", 350, 530, WHITE)


def update_projectiles(shield_active):
    global player_health

    for projectile in projectiles[:]:
        rect = projectile["rect"]
        rect.x += projectile["dx"]
        rect.y += projectile["dy"]

        if rect.colliderect(player):
            if not shield_active:
                player_health -= projectile["damage"]

            projectiles.remove(projectile)

        elif not screen.get_rect().colliderect(rect):
            projectiles.remove(projectile)

    player_health = max(0, player_health)


while running:

    clock.tick(60)
    current_time = pygame.time.get_ticks()

    shield_active = current_time < shield_until
    speed_active = current_time < speed_until

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                if terminal_open:
                    terminal_open = False
                elif inventory_open:
                    inventory_open = False
                elif show_help:
                    show_help = False
                elif game_won:
                    running = False

            elif event.key == pygame.K_F1 and not game_won:
                show_help = not show_help

            elif terminal_open:

                if event.key == pygame.K_BACKSPACE:
                    code_input = code_input[:-1]

                elif event.key == pygame.K_RETURN:
                    check_terminal()

                elif event.unicode and event.unicode.isprintable():
                    code_input += event.unicode

            elif not inventory_open and not show_help and not game_won:

                if event.key == pygame.K_i:
                    inventory_open = True

                elif event.key == pygame.K_1:
                    use_emp(current_time)

                elif event.key == pygame.K_2:
                    activate_shield(current_time)

                elif event.key == pygame.K_3:
                    activate_speed_boost(current_time)

                elif event.key == pygame.K_SPACE:
                    player_attack(current_time)

                elif event.key == pygame.K_h:
                    if "energy_pack" in inventory:
                        inventory.remove("energy_pack")
                        player_energy = min(100, player_energy + 40)
                        player_health = min(100, player_health + 20)

                elif event.key == pygame.K_j:
                    if "access_card" in inventory:
                        feedback = "Access card found!"
                    else:
                        feedback = "Access card not found."

                elif event.key == pygame.K_e:
                    for terminal_id, rect in terminals.items():
                        if distance_between(player, rect) < 80:
                            open_terminal(terminal_id)
                            break

    if not terminal_open and not inventory_open and not show_help and not game_won:

        keys = pygame.key.get_pressed()
        speed = 7 if speed_active else player_speed

        dx = 0
        dy = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = speed

        player.x += dx

        for wall in walls:
            if player.colliderect(wall):
                player.x -= dx

        player.y += dy

        for wall in walls:
            if player.colliderect(wall):
                player.y -= dy

        player.clamp_ip(screen.get_rect())

        for item in items[:]:
            if player.colliderect(item["rect"]):
                inventory.append(item["name"])
                items.remove(item)

        if boss_unlocked:
            boss.update(current_time, player)
            update_projectiles(shield_active)

            if boss.alive and player.colliderect(boss.rect) and not shield_active:
                player_health -= 1

            if not boss.alive:
                game_won = True
                xp += 300
                credits += 300

        else:
            for robot in robots:
                damage = robot.update(player, current_time, shield_active)

                if damage:
                    player_health -= 1

        player_health = max(0, player_health)

        if player_health <= 0:
            player_health = 100
            player.x, player.y = 70, 70
            projectiles.clear()

    if game_won:
        draw_victory_screen()
    else:
        draw_world()
        draw_ability_status(current_time)

        if terminal_open:
            draw_terminal()

        if inventory_open:
            draw_inventory()

        if show_help:
            draw_help()

        if boss_unlocked and boss.alive:
            draw_text("FINAL BOSS: Use SPACE to attack. Dodge orange projectiles!", 220, 625, YELLOW, small_font)

    pygame.display.flip()


pygame.quit()
