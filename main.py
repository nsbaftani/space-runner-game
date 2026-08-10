#    high_score = Text(text="High Score: %d" % score,position=(-0.85, 0.35), color=color.blue)
from ursina import *
import random
import json
import os
import atexit

app = Ursina()

# --- بخش صدا ---
# نکته: نام فایل‌ها را حتماً مطابق فایل‌های خودت چک کن
try:
    background_music = Audio('GAmer.mp3', loop=True, autoplay=True)
    game_over_sound = Audio('Game-Over-Voice-Scary-Sound2.mp3', autoplay=False)
except:
    background_music = None
    game_over_sound = None

# --- تنظیمات اولیه دوربین ---
camera.position = (0, 10, -20)
camera.rotation_x = 20

# --- متغیرهای اصلی بازی ---
score = 0
level = 1
speed = 10
game_over = False
player_choice = None
is_restarting = False

# --- High Score ---
high_score = 0

# --- لیست تم‌ها ---
LEVEL_THEMES = [
    (color.dark_gray, color.red, color.orange, color.black),
    (color.green, color.yellow, color.lime, color.azure),
    (color.black, color.magenta, color.cyan, color.red),
    (color.green, color.white, color.azure, color.dark_gray),
    (color.rgb(50, 0, 50), color.gold, color.white, color.black)
]

# --- اشیاء بازی ---
ship = None
ground = None
score_text = None
level_text = None
high_score_text = None
game_over_text = None
instructions_text = None
obstacles = []

target_ground_color = color.dark_gray
target_obs_color = color.red
target_ship_color = color.orange
target_sky_color = color.black


# --- توابع High Score ---
def load_high_score():
    global high_score
    try:
        if os.path.exists("highscore.json"):
            with open("highscore.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                high_score = int(data.get("high_score", 0))
        else:
            high_score = 0
    except Exception as e:
        print(f"Error loading high score: {e}")
        high_score = 0


def save_high_score():
    global high_score
    try:
        with open("highscore.json", "w", encoding="utf-8") as f:
            json.dump({"high_score": int(high_score)}, f)
    except Exception as e:
        print(f"Error saving high score: {e}")


# بارگذاری High Score در شروع برنامه
load_high_score()


def smooth_color_transition():
    global target_ground_color, target_obs_color, target_ship_color, target_sky_color
    theme_idx = min(level - 1, len(LEVEL_THEMES) - 1)
    bg_c, obs_c, ship_c, sky_c = LEVEL_THEMES[theme_idx]
    target_ground_color = bg_c
    target_obs_color = obs_c
    target_ship_color = ship_c
    target_sky_color = sky_c

    if ground: ground.color = lerp(ground.color, target_ground_color, time.dt * 0.5)
    if ship: ship.color = lerp(ship.color, target_ship_color, time.dt * 0.5)
    for o in obstacles:
        if o: o.color = lerp(o.color, target_obs_color, time.dt * 0.5)
    window.color = lerp(window.color, target_sky_color, time.dt * 0.5)


def restart_game():
    global score, level, game_over, player_choice, ship, ground, obstacles, \
        target_ground_color, target_obs_color, target_ship_color, target_sky_color, is_restarting
    is_restarting = True
    score = 0
    level = 1
    game_over = False
    target_ground_color, target_obs_color, target_ship_color, target_sky_color = LEVEL_THEMES[0]
    window.color = target_sky_color
    if ship: destroy(ship); ship = None
    if ground: destroy(ground); ground = None
    for o in obstacles: destroy(o)
    obstacles.clear()
    player_choice = None
    show_start_menu()
    invoke(finalize_restart, delay=0.2)


def finalize_restart():
    global is_restarting
    is_restarting = False


def show_start_menu():
    global player_choice, game_over_text, instructions_text, score_text, level_text, high_score_text
    player_choice = None
    if score_text: score_text.enabled = False
    if level_text: level_text.enabled = False
    if high_score_text: high_score_text.enabled = False
    if game_over_text: game_over_text.enabled = False
    if instructions_text:
        destroy(instructions_text)
        instructions_text = None
    # راهنمای اضافه شده برای موبایل
    instructions_text = Text(text=f"PC: 'K' (Keyboard) or 'M' (Mouse)\nMobile: Just Tap to Start\n\nHigh Score: {high_score}",
                             origin=(0, 0), scale=1.5, color=color.white)


def start_game():
    global ship, ground, score_text, level_text, high_score_text, game_over_text, instructions_text, player_choice, \
        target_ground_color, target_obs_color, target_ship_color, target_sky_color
    if instructions_text:
        destroy(instructions_text)
        instructions_text = None
    target_ground_color, target_obs_color, target_ship_color, target_sky_color = LEVEL_THEMES[0]
    window.color = target_sky_color
    ship = Entity(model='cube', color=target_ship_color, scale=(2, 0.5, 2), z=0, collider='box')
    ground = Entity(model='plane', scale=1000, texture='white_cube', texture_scale=(100, 100),
                    color=target_ground_color)

    score_text = Text(text='Score: 0', position=(-0.85, 0.45), scale=2, color=color.white)
    level_text = Text(text='Level: 1', position=(-0.85, 0.40), scale=1.5, color=color.yellow)
    high_score_text = Text(text=f'High Score: {high_score}', position=(-0.85, 0.35), scale=1.5, color=color.cyan)
    game_over_text = Text(text="GAME OVER\nTap/Space to restart", origin=(0, 0), scale=2.5, color=color.red,
                          enabled=False)


# این خط را بالای تابع update یا کنار obstacles اضافه کن
trails = []


def update():
    global score, level, speed, game_over, player_choice, ship, is_restarting, trails, high_score

    if is_restarting: return

    if ship is None:
        if game_over and (held_keys['space'] or mouse.left):
            restart_game()
        return

    if game_over:
        background_music.stop()
        if held_keys['space'] or mouse.left:
            restart_game()
            background_music.play()
        return

    # --- بخش اول: تشخیص بوست و سرعت ---
    is_boosting = False

    # تشخیص بوست برای کامپیوتر
    if player_choice == 'keyboard' and held_keys['w']:
        is_boosting = True
        current_speed = speed * 3
    # تشخیص بوست برای موس (راست کلیک)
    elif player_choice == 'mouse' and mouse.right:
        is_boosting = True
        current_speed = speed * 2
    # تشخیص بوست برای موبایل (شبیه‌سازی دو انگشت با استفاده از منطق لمس)
    # نکته: در Ursina برای موبایل تشخیص دقیق دو انگشت کمی پیچیده است،
    # اما اگر دو لمس همزمان داشته باشی، این بخش فعال می‌شود
    elif player_choice == 'mouse' and mouse.left and held_keys[
        'shift']:  # در حالت موبایل معمولاً shift یا لمس دوم هندل می‌شود
        is_boosting = True
        current_speed = speed * 3
    else:
        current_speed = speed

    ship.z += current_speed * time.dt

    # --- بخش دوم: ایجاد رد (Trail Effect) ---
    if is_boosting:
        # ایجاد یک قطعه کوچک از رد در موقعیت فعلی سفینه
        new_trail = Entity(
            model='quad',
            color=color.cyan.tint(-.5),  # رنگ کمرنگ‌تر از رنگ سفینه
            scale=(1, 0.5),
            position=(ship.x, ship.y, ship.z),
            rotation_x=90,  # برای اینکه تخت روی زمین یا پشت سفینه باشد
            render_queue=1  # برای اینکه زیر سفینه باشد
        )
        trails.append(new_trail)

        # کم کردن عمر ردها (برای اینکه از بین بروند)
        for t in trails[:]:
            t.alpha -= time.dt * 2  # سرعت محو شدن
            if t.alpha <= 0:
                trails.remove(t)
                destroy(t)
    else:
        # اگر بوست نبود، ردها سریع‌تر محو شوند
        for t in trails[:]:
            t.alpha -= time.dt * 5
            if t.alpha <= 0:
                trails.remove(t)
                destroy(t)

    # --- ادامه کدهای قبلی تو بدون تغییر ---
    score = int(ship.z)
    score_text.text = f'Score: {score}'

    # --- به‌روزرسانی High Score ---
    if score > high_score:
        high_score = score
        if high_score_text:
            high_score_text.text = f'High Score: {high_score}'
        save_high_score()

    new_level = (score // 200) + 1
    if new_level > level:
        level = new_level
        level_text.text = f'Level: {level}'

    camera.z = ship.z - 20
    smooth_color_transition()

    if player_choice == 'keyboard':
        ship.x += (held_keys['d'] - held_keys['a']) * 15 * time.dt
    elif player_choice == 'mouse':
        ship.x = mouse.x * 30
        # (بخش مربوط به سرعت در بالا مدیریت شد تا تداخل نداشته باشد)

    if mouse.left and player_choice is None:
        pass
    elif mouse.left:
        target_x = mouse.x * 30
        ship.x = lerp(ship.x, target_x, time.dt * 10)

    ship.x = clamp(ship.x, -18, 18)

    theme_idx = min(level - 1, len(LEVEL_THEMES) - 1)
    obs_color = LEVEL_THEMES[theme_idx][1]

    spawn_chance = 0.05 + (level * 0.01)
    if random.random() < spawn_chance:
        obstacle = Entity(model='cube', color=obs_color, scale=(3, 3, 3),
                          position=(random.randint(-15, 15), 1.5, ship.z + 100),
                          collider='box')
        obstacles.append(obstacle)

    for o in obstacles[:]:
        if o.enabled and ship.intersects(o).hit:
            game_over = True
            game_over_text.enabled = True
            game_over_text.text = f"GAME OVER\nScore: {score}\nHigh Score: {high_score}\n\nTap/Space to restart"
            save_high_score()
            if game_over_sound: game_over_sound.play()
            for obs in obstacles:
                obs.enabled = False
            break

        if o.z < ship.z - 10:
            if o in obstacles:
                destroy(o)
                obstacles.remove(o)


# ذخیره High Score هنگام بستن برنامه (حتی با دکمه ضربدر)
atexit.register(save_high_score)


def input(key):
    global player_choice
    if key == 'escape':
        save_high_score()
    if player_choice is None and not is_restarting:
        # در کامپیوتر با K یا M
        if key == 'k':
            player_choice = 'keyboard'
            start_game()
        elif key == 'm':
            player_choice = 'mouse'
            start_game()
        # در موبایل با اولین لمس صفحه (click یا touch)
        elif key == 'left mouse down':
            player_choice = 'mouse'  # برای موبایل بهترین حالت همان حالت موس/لمس است
            start_game()


show_start_menu()
app.run()
