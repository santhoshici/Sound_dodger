import pygame
import random
import numpy as np
import sounddevice as sd

# Initialize Pygame
pygame.init()

# Game constants
WIDTH, HEIGHT = 800, 400
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BASE_GRAVITY = 10
JUMP_STRENGTH = 15
BASE_OBSTACLE_SPEED = 5
SPEED_INCREMENT = 0.005  # Speed increases over time
FRAME_DELAY = 5
NUM_FRAMES = 4
FPS = 30
DAY_NIGHT_CYCLE = 1000  # Time in frames for day/night cycle
POWERUP_DURATION = 300  # Duration of power-ups in frames
LEADERBOARD_FILE = "leaderboard.txt"  # File to store top 3 high scores

# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Sound Dodge Jungle 🌿")
font = pygame.font.Font(None, 36)

# Load game assets
try:
    day_background = pygame.image.load("jungle_background.png")
    night_background = pygame.image.load("jungle_night.png")
    day_background = pygame.transform.scale(day_background, (WIDTH, HEIGHT))
    night_background = pygame.transform.scale(night_background, (WIDTH, HEIGHT))
    player_sheet = pygame.image.load("runner_spritesheet.png")
    log_img = pygame.image.load("log.png")
    vine_img = pygame.image.load("vine.png")
    bush_img = pygame.image.load("bush.png")
    speed_boost_img = pygame.image.load("speed_boost.png")
    invincibility_img = pygame.image.load("invincibility.png")
except pygame.error as e:
    print(f"Error loading assets: {e}")
    pygame.quit()
    exit()

# Prepare player sprites
sprite_width = player_sheet.get_width() // NUM_FRAMES
sprite_height = player_sheet.get_height()
player_sprites = [pygame.transform.scale(player_sheet.subsurface(pygame.Rect(i * sprite_width, 0, sprite_width, sprite_height)), (60, 80)) for i in range(NUM_FRAMES)]

# Scale obstacle images
log_img = pygame.transform.scale(log_img, (80, 40))
vine_img = pygame.transform.scale(vine_img, (100, 20))
bush_img = pygame.transform.scale(bush_img, (70, 50))
speed_boost_img = pygame.transform.scale(speed_boost_img, (40, 40))
invincibility_img = pygame.transform.scale(invincibility_img, (40, 40))

# Sound-based input
sound_intensity = 0

def get_sound_intensity(indata, frames, time, status):
    """Callback function to calculate sound intensity from microphone input."""
    global sound_intensity
    volume_norm = np.linalg.norm(indata) * 10
    sound_intensity = min(volume_norm / 5, 3)

try:
    stream = sd.InputStream(callback=get_sound_intensity, channels=1)
    stream.start()
except Exception as e:
    print(f"Error initializing sound input: {e}")
    sound_intensity = 1  # Fallback to constant intensity if sound fails

class Player:
    """Player class to handle player movement, jumping, and drawing."""
    def __init__(self):
        self.x = 100
        self.y = HEIGHT - 80
        self.width = 60
        self.height = 80
        self.velocity_y = 0
        self.on_ground = True
        self.sprite_index = 0
        self.frame_count = 0
        self.is_invincible = False
        self.invincibility_timer = 0
        self.speed_boost_timer = 0
        self.flash_timer = 0  # For invincibility flicker effect

    def update(self, gravity):
        """Update player position and velocity."""
        self.velocity_y += gravity
        self.y += self.velocity_y

        # Keep player on the ground and within screen bounds
        if self.y >= HEIGHT - self.height:
            self.y = HEIGHT - self.height
            self.velocity_y = 0
            self.on_ground = True
        elif self.y < 0:  # Prevent player from jumping out of the screen
            self.y = 0
            self.velocity_y = 0

        # Keep player on the left half of the screen
        if self.x < 0:
            self.x = 0
        elif self.x > WIDTH // 2 - self.width:
            self.x = WIDTH // 2 - self.width

        # Update timers for power-ups
        if self.is_invincible:
            self.invincibility_timer -= 1
            if self.invincibility_timer <= 0:
                self.is_invincible = False

        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= 1

        # Flicker effect for invincibility
        if self.is_invincible:
            self.flash_timer += 1
            if self.flash_timer >= 10:  # Flicker every 10 frames
                self.flash_timer = 0

    def jump(self, jump_strength):
        """Make the player jump based on sound intensity."""
        if self.on_ground:
            self.velocity_y = -jump_strength * min(sound_intensity, 2)

    def draw(self):
        """Draw the player sprite with animation."""
        self.frame_count += 1
        if self.frame_count % FRAME_DELAY == 0:
            self.sprite_index = (self.sprite_index + 1) % NUM_FRAMES

        # Flicker effect for invincibility
        if self.is_invincible and self.flash_timer < 5:
            return  # Skip drawing to create a flicker effect

        screen.blit(player_sprites[self.sprite_index], (self.x, int(self.y)))

    def apply_speed_boost(self):
        """Apply speed boost effect to the player."""
        self.speed_boost_timer = POWERUP_DURATION

    def apply_invincibility(self):
        """Apply invincibility effect to the player."""
        self.is_invincible = True
        self.invincibility_timer = POWERUP_DURATION

class Obstacle:
    """Obstacle class to handle obstacles like logs, vines, and bushes."""
    def __init__(self, speed, obstacle_type):
        self.x = WIDTH
        self.speed = speed * random.uniform(1.2, 1.8)
        self.type = obstacle_type

        # Set obstacle image and position based on type
        if self.type == "log":
            self.image = log_img
            self.y = HEIGHT - 50
        elif self.type == "vine":
            self.image = vine_img
            self.y = random.randint(50, 70)
        elif self.type == "bush":
            self.image = bush_img
            self.y = HEIGHT - 60

        self.width = self.image.get_width()
        self.height = self.image.get_height()

    def update(self):
        """Move the obstacle and check if it's off-screen."""
        self.x -= self.speed
        return self.x > -self.width

    def draw(self):
        """Draw the obstacle on the screen."""
        screen.blit(self.image, (self.x, self.y))

class PowerUp:
    """Power-up class to handle speed boosts and invincibility."""
    def __init__(self, speed, powerup_type):
        self.x = WIDTH
        self.speed = speed
        self.type = powerup_type
        self.image = speed_boost_img if powerup_type == "speed_boost" else invincibility_img
        self.y = HEIGHT - 60
        self.width = self.image.get_width()
        self.height = self.image.get_height()

    def update(self):
        """Move the power-up and check if it's off-screen."""
        self.x -= self.speed
        return self.x > -self.width

    def draw(self):
        """Draw the power-up on the screen."""
        screen.blit(self.image, (self.x, self.y))

def check_collision(player, obstacles):
    """Check if the player collides with any obstacle."""
    if player.is_invincible:
        return False
    player_rect = pygame.Rect(player.x, int(player.y), player.width, player.height)
    for obstacle in obstacles:
        obstacle_rect = pygame.Rect(obstacle.x, obstacle.y, obstacle.width, obstacle.height)
        if player_rect.colliderect(obstacle_rect):
            return True
    return False

def draw_sound_intensity_bar(sound_intensity):
    """Draw a visual bar to show the current sound intensity."""
    bar_width = 200
    bar_height = 20
    bar_x = WIDTH - bar_width - 10
    bar_y = 10
    pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height), 2)
    fill_width = int(sound_intensity * (bar_width / 3))
    pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, fill_width, bar_height))

def draw_powerup_timers(player):
    """Draw timers for active power-ups."""
    if player.speed_boost_timer > 0:
        speed_boost_text = font.render(f"Speed Boost: {player.speed_boost_timer // FPS}", True, BLACK)
        screen.blit(speed_boost_text, (10, HEIGHT - 50))

    if player.invincibility_timer > 0:
        invincibility_text = font.render(f"Invincibility: {player.invincibility_timer // FPS}", True, BLACK)
        screen.blit(invincibility_text, (10, HEIGHT - 80))

def load_leaderboard():
    """Load the top 3 high scores from the leaderboard file."""
    try:
        with open(LEADERBOARD_FILE, "r") as file:
            scores = [int(line.strip()) for line in file.readlines()]
            scores.sort(reverse=True)
            return scores[:3]  # Return top 3 scores
    except FileNotFoundError:
        return [0, 0, 0]  # Default scores if file doesn't exist

def save_leaderboard(scores):
    """Save the top 3 high scores to the leaderboard file."""
    with open(LEADERBOARD_FILE, "w") as file:
        for score in scores:
            file.write(f"{score}\n")

def update_leaderboard(new_score):
    """Update the leaderboard with a new score if it's in the top 3."""
    scores = load_leaderboard()
    scores.append(new_score)
    scores.sort(reverse=True)
    save_leaderboard(scores[:3])  # Save only the top 3 scores

def show_leaderboard():
    """Display the leaderboard on the screen."""
    scores = load_leaderboard()
    screen.fill(WHITE)
    leaderboard_text = font.render("Leaderboard", True, BLACK)
    screen.blit(leaderboard_text, (WIDTH // 2 - 80, 50))

    for i, score in enumerate(scores):
        score_text = font.render(f"{i + 1}. {score}", True, BLACK)
        screen.blit(score_text, (WIDTH // 2 - 50, 100 + i * 50))

    back_text = font.render("Press B to Go Back", True, BLACK)
    screen.blit(back_text, (WIDTH // 2 - 100, HEIGHT - 100))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:
                    return True

def pause_menu():
    """Display the pause menu and handle user input."""
    screen.fill(WHITE)
    pause_text = font.render("Paused", True, BLACK)
    resume_text = font.render("Press R to Resume", True, BLACK)
    quit_text = font.render("Press Q to Quit", True, BLACK)

    screen.blit(pause_text, (WIDTH // 2 - 50, HEIGHT // 2 - 50))
    screen.blit(resume_text, (WIDTH // 2 - 100, HEIGHT // 2))
    screen.blit(quit_text, (WIDTH // 2 - 80, HEIGHT // 2 + 50))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key == pygame.K_q:
                    return False

def game_over_screen(score, high_score):
    """Display the game over screen and handle user input."""
    screen.fill(WHITE)
    game_over_text = font.render("Game Over!", True, BLACK)
    score_text = font.render(f"Score: {score}", True, BLACK)
    high_score_text = font.render(f"High Score: {high_score}", True, BLACK)
    restart_text = font.render("Press R to Restart", True, BLACK)
    quit_text = font.render("Press Q to Quit", True, BLACK)

    screen.blit(game_over_text, (WIDTH // 2 - 80, HEIGHT // 2 - 50))
    screen.blit(score_text, (WIDTH // 2 - 50, HEIGHT // 2))
    screen.blit(high_score_text, (WIDTH // 2 - 80, HEIGHT // 2 + 50))
    screen.blit(restart_text, (WIDTH // 2 - 100, HEIGHT // 2 + 100))
    screen.blit(quit_text, (WIDTH // 2 - 80, HEIGHT // 2 + 150))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key == pygame.K_q:
                    return False

def main():
    """Main game loop."""
    clock = pygame.time.Clock()
    player = Player()
    obstacles = []
    powerups = []
    score = 0
    high_score = 0
    running = True
    paused = False
    bg_x = 0
    gravity = BASE_GRAVITY
    is_day = True
    cycle_counter = 0
    score_multiplier = 1
    consecutive_obstacles_avoided = 0

    while running:
        if not paused:
            # Draw background
            screen.fill(WHITE)
            background = day_background if is_day else night_background
            screen.blit(background, (bg_x, 0))
            screen.blit(background, (bg_x + WIDTH, 0))
            bg_x -= int(2 + (score / 1000))  # Dynamic background scrolling
            if bg_x <= -WIDTH:
                bg_x = 0

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:  # Pause the game
                        paused = True
                    if event.key == pygame.K_l:  # Show leaderboard
                        if not show_leaderboard():
                            running = False

            # Day/Night cycle
            cycle_counter += 1
            if cycle_counter >= DAY_NIGHT_CYCLE:
                is_day = not is_day
                cycle_counter = 0

            # Jump based on sound intensity
            player.jump(JUMP_STRENGTH)
            player.update(gravity)

            # Spawn obstacles and power-ups
            obstacle_speed = BASE_OBSTACLE_SPEED + (SPEED_INCREMENT * score)
            if len(obstacles) < 2 and random.randint(1, 50) == 1:
                obstacle_type = random.choice(["log", "vine", "bush"])
                obstacles.append(Obstacle(obstacle_speed, obstacle_type))

            if len(powerups) < 1 and random.randint(1, 200) == 1:
                powerup_type = random.choice(["speed_boost", "invincibility"])
                powerups.append(PowerUp(obstacle_speed, powerup_type))

            # Update and draw obstacles
            for obstacle in obstacles[:]:
                if not obstacle.update():
                    obstacles.remove(obstacle)
                    consecutive_obstacles_avoided += 1
                    if consecutive_obstacles_avoided >= 5:
                        score_multiplier += 0.1
                        consecutive_obstacles_avoided = 0

            # Update and draw power-ups
            for powerup in powerups[:]:
                if not powerup.update():
                    powerups.remove(powerup)
                else:
                    powerup.draw()

            # Check for collisions with power-ups
            player_rect = pygame.Rect(player.x, int(player.y), player.width, player.height)
            for powerup in powerups[:]:
                powerup_rect = pygame.Rect(powerup.x, powerup.y, powerup.width, powerup.height)
                if player_rect.colliderect(powerup_rect):
                    if powerup.type == "speed_boost":
                        player.apply_speed_boost()
                    elif powerup.type == "invincibility":
                        player.apply_invincibility()
                    powerups.remove(powerup)

            # Check for collisions with obstacles
            if check_collision(player, obstacles):
                if score > high_score:
                    high_score = score
                    update_leaderboard(high_score)  # Update leaderboard
                if not game_over_screen(score, high_score):
                    running = False
                else:
                    # Reset game state
                    player = Player()
                    obstacles = []
                    powerups = []
                    score = 0
                    bg_x = 0
                    cycle_counter = 0
                    score_multiplier = 1
                    consecutive_obstacles_avoided = 0

            # Draw player and obstacles
            player.draw()
            for obstacle in obstacles:
                obstacle.draw()

            # Display score and multiplier
            score += int(1 * score_multiplier)
            text = font.render(f"Score: {score}", True, BLACK)
            screen.blit(text, (10, 10))
            multiplier_text = font.render(f"Multiplier: x{score_multiplier:.1f}", True, BLACK)
            screen.blit(multiplier_text, (10, 50))

            # Draw sound intensity bar
            draw_sound_intensity_bar(sound_intensity)

            # Draw power-up timers
            draw_powerup_timers(player)

            pygame.display.flip()
            clock.tick(FPS)
        else:
            if not pause_menu():
                running = False
            paused = False

    pygame.quit()

if __name__ == "__main__":
    main()
