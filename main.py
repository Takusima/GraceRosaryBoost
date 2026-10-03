import ctypes
import ctypes.wintypes
import json
import os
import random
import threading
import time
import tkinter as tk
from pynput import mouse

W, H = 220, 220
CONFIG_FILE = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "GraceRosaryBoost", "settings.json")

# Set this to the scan code used by the in-game Rosary action.
SCAN_CODE = 0x11

THEMES = {
    "sorrow": {"bg": "#000000", "idle": "#333333", "dim": "#222222", "accent": "#ff0000", "border": "#1a1a1a", "rain": True, "font": "Impact"},
    "coko": {"bg": "#0b0d10", "idle": "#6d7480", "dim": "#30353c", "accent": "#d9e6f2", "border": "#3c4652", "rain": False, "font": "Segoe UI"},
}

current_theme = "sorrow"
is_active = False
selected_button = "M5"
cps_value = "30"
follow_roblox = True
follow_preset = "bottom-right"
saved_x = saved_y = None
drag_offset = None
dragging = False
pulse_val = 0.0
pulse_dir = 1
drops = []
roblox_hwnd = None
last_roblox_rect = None


def load_settings():
    global current_theme, selected_button, cps_value, follow_roblox, follow_preset, saved_x, saved_y
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("theme") in THEMES:
            current_theme = data["theme"]
        if data.get("button") in ("M4", "M5"):
            selected_button = data["button"]
        cps_value = str(max(1, min(100, int(data.get("cps", 30)))))
        follow_roblox = bool(data.get("follow_roblox", True))
        follow_preset = data.get("preset", "bottom-right")
        saved_x, saved_y = data.get("x"), data.get("y")
    except Exception:
        pass


def save_settings():
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "theme": current_theme, "button": selected_button, "cps": int(cps_value or 30),
                "follow_roblox": follow_roblox, "preset": follow_preset,
                "x": root.winfo_x(), "y": root.winfo_y()
            }, f, indent=2)
    except Exception:
        pass


def press_key_raw(code):
    if not code:
        return
    ctypes.windll.user32.keybd_event(0, code, 0x0008, 0)
    time.sleep(0.01)
    ctypes.windll.user32.keybd_event(0, code, 0x0008 | 0x0002, 0)


def spam_loop():
    while True:
        if is_active:
            try:
                val = max(1, min(100, int(cps_value)))
            except Exception:
                val = 30
            press_key_raw(SCAN_CODE)
            time.sleep(1.0 / val)
        else:
            time.sleep(0.05)


def find_roblox():
    global roblox_hwnd
    user32 = ctypes.windll.user32
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if "roblox" in buf.value.lower():
                found.append(hwnd)
                return False
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    roblox_hwnd = found[0] if found else None
    return roblox_hwnd


def get_window_rect(hwnd):
    if not hwnd:
        return None
    rect = ctypes.wintypes.RECT()
    if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return rect.left, rect.top, rect.right, rect.bottom
    return None


def set_overlay_topmost(enabled):
    flags = 0x0001 | 0x0002 | 0x0010
    insert_after = -1 if enabled else -2
    ctypes.windll.user32.SetWindowPos(root.winfo_id(), insert_after, 0, 0, 0, 0, flags)


def position_relative(rect):
    global saved_x, saved_y
    if not rect:
        return
    left, top, right, bottom = rect
    margin = 14
    positions = {
        "top-left": (left + margin, top + margin),
        "top-right": (right - W - margin, top + margin),
        "bottom-left": (left + margin, bottom - H - margin),
        "bottom-right": (right - W - margin, bottom - H - margin),
        "center": (left + (right - left - W) // 2, top + (bottom - top - H) // 2),
    }
    saved_x, saved_y = positions.get(follow_preset, positions["bottom-right"])
    root.geometry(f"{W}x{H}+{saved_x}+{saved_y}")


def follow_roblox_loop():
    global last_roblox_rect
    hwnd = find_roblox()
    rect = get_window_rect(hwnd)
    focused = is_window_foreground(hwnd)
    if rect:
        if follow_roblox and not dragging:
            if rect != last_roblox_rect:
                position_relative(rect)
            last_roblox_rect = rect
        set_overlay_topmost(bool(focused or is_active))
    else:
        set_overlay_topmost(False)
    root.after(250, follow_roblox_loop)


def is_window_foreground(hwnd):
    return bool(hwnd) and ctypes.windll.user32.GetForegroundWindow() == hwnd


def interpolate_color(a, b, progress):
    r1, g1, b1 = root.winfo_rgb(a)
    r2, g2, b2 = root.winfo_rgb(b)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * progress) >> 8,
        int(g1 + (g2 - g1) * progress) >> 8,
        int(b1 + (b2 - b1) * progress) >> 8)


def update_button_colors():
    t = THEMES[current_theme]
    color = t["accent"] if is_active else t["accent"]
    rain_canvas.itemconfig(m4_text, fill=color if selected_button == "M4" else t["dim"])
    rain_canvas.itemconfig(m5_text, fill=color if selected_button == "M5" else t["dim"])


def apply_theme():
    t = THEMES[current_theme]
    root.configure(bg=t["bg"], highlightbackground=t["border"])
    rain_canvas.configure(bg=t["bg"])
    close_button.configure(bg=t["bg"], fg=t["dim"], activebackground=t["bg"])
    menu_button.configure(bg=t["bg"], fg=t["dim"], activebackground=t["bg"])
    rain_canvas.itemconfig(title_text, fill=t["idle"], font=(t["font"], 28))
    rain_canvas.itemconfig(cps_display, fill=t["idle"], font=(t["font"], 56))
    update_button_colors()


def attack_visuals():
    global pulse_val, pulse_dir
    t = THEMES[current_theme]
    if is_active:
        pulse_val += 0.05 * pulse_dir
        if pulse_val >= 1:
            pulse_dir = -1
        if pulse_val <= 0:
            pulse_dir = 1
        if current_theme == "sorrow":
            flash = random.random() > 0.96
            bg = "#330000" if flash else interpolate_color("#000000", "#120000", pulse_val)
            fg = "#ff0000" if flash else interpolate_color("#660000", "#ff0000", pulse_val)
        else:
            bg = interpolate_color("#0b0d10", "#1c242d", pulse_val)
            fg = interpolate_color("#a9bfd2", "#f2f7fb", pulse_val)
        rain_canvas.configure(bg=bg)
        close_button.configure(bg=bg)
        menu_button.configure(bg=bg)
        dx, dy = random.randint(-1, 1), random.randint(-1, 1)
        rain_canvas.coords(title_text, W // 2 + dx, 45 + dy)
        rain_canvas.coords(cps_display, W // 2 - dx, 115 + dy)
        rain_canvas.itemconfig(title_text, fill=fg)
        rain_canvas.itemconfig(cps_display, fill=fg)
        rain_canvas.itemconfig(m4_text, fill=fg if selected_button == "M4" else t["dim"])
        rain_canvas.itemconfig(m5_text, fill=fg if selected_button == "M5" else t["dim"])
        root.config(highlightbackground=fg)
    else:
        rain_canvas.configure(bg=t["bg"])
        close_button.configure(bg=t["bg"])
        menu_button.configure(bg=t["bg"])
        rain_canvas.coords(title_text, W // 2, 45)
        rain_canvas.coords(cps_display, W // 2, 115)
        rain_canvas.itemconfig(title_text, fill=t["idle"])
        rain_canvas.itemconfig(cps_display, fill=t["idle"])
        update_button_colors()
        root.config(highlightbackground=t["border"])
    root.after(40, attack_visuals)


def create_rain():
    for _ in range(80):
        x, y = random.randint(-50, 250), random.randint(-220, 220)
        length = random.randint(40, 70)
        drop = rain_canvas.create_line(x, y, x - 3, y + length, fill="#0a0a0a", width=1)
        drops.append([drop, random.randint(5, 12), length])


def animate_rain():
    for drop_obj, speed, length in drops:
        if current_theme == "coko":
            rain_canvas.itemconfig(drop_obj, state="hidden")
            continue
        rain_canvas.itemconfig(drop_obj, state="normal")
        actual_speed = speed * 3.5 if is_active else speed
        color = random.choice(["#ff0000", "#8b0000", "#4a0000"]) if is_active else "#111111"
        rain_canvas.move(drop_obj, -1 if is_active else 0, actual_speed)
        rain_canvas.itemconfig(drop_obj, fill=color, width=1.5 if is_active else 1)
        c = rain_canvas.coords(drop_obj)
        if c and c[3] > H:
            nx = random.randint(-50, 250)
            rain_canvas.coords(drop_obj, nx, -80, nx - 3, -80 + length)
    root.after(35, animate_rain)


def start_drag(event):
    global drag_offset, dragging
    if event.widget in (close_button, menu_button):
        return
    drag_offset = (event.x_root - root.winfo_x(), event.y_root - root.winfo_y())
    dragging = True


def drag_window(event):
    if drag_offset is not None:
        root.geometry(f"{W}x{H}+{event.x_root - drag_offset[0]}+{event.y_root - drag_offset[1]}")


def stop_drag(_event):
    global dragging, drag_offset
    dragging = False
    drag_offset = None
    save_settings()


def set_preset(preset):
    global follow_preset, follow_roblox
    follow_preset, follow_roblox = preset, True
    rect = get_window_rect(find_roblox())
    if rect:
        position_relative(rect)
    save_settings()


def toggle_follow():
    global follow_roblox
    follow_roblox = not follow_roblox
    save_settings()


def choose_theme(theme):
    global current_theme
    current_theme = theme
    apply_theme()
    save_settings()


def set_cps(value):
    global cps_value
    cps_value = str(max(1, min(100, int(value))))
    rain_canvas.itemconfig(cps_display, text=cps_value)
    save_settings()


def on_key(event):
    global cps_value
    if is_active:
        return
    if event.keysym == "BackSpace":
        cps_value = cps_value[:-1] or "0"
    elif event.char.isdigit() and len(cps_value) < 3:
        cps_value += event.char
    cps_value = str(max(0, min(100, int(cps_value))))
    rain_canvas.itemconfig(cps_display, text=cps_value)
    save_settings()


def on_canvas_click(event):
    global selected_button
    if 165 < event.y < 205:
        if 35 < event.x < 105:
            selected_button = "M4"
        elif 115 < event.x < 185:
            selected_button = "M5"
        update_button_colors()
        save_settings()


def on_mouse_click(x, y, button, pressed):
    global is_active
    if pressed:
        target = mouse.Button.x1 if selected_button == "M4" else mouse.Button.x2
        if button == target:
            is_active = not is_active
            if is_active:
                set_overlay_topmost(True)
            save_settings()


def make_position_menu(parent):
    sub = tk.Menu(parent, tearoff=0)
    for key, label in [("top-left", "Top left"), ("top-right", "Top right"),
                       ("bottom-left", "Bottom left"), ("bottom-right", "Bottom right"),
                       ("center", "Center")]:
        sub.add_command(label=label, command=lambda p=key: set_preset(p))
    return sub


def show_menu(event=None):
    t = THEMES[current_theme]
    menu = tk.Menu(root, tearoff=0, bg=t["bg"], fg=t["idle"],
                   activebackground=t["border"], activeforeground=t["accent"])
    menu.add_command(label=f"Theme: {current_theme.title()}", state="disabled")
    menu.add_separator()
    menu.add_command(label="Sorrow", command=lambda: choose_theme("sorrow"))
    menu.add_command(label="Coko", command=lambda: choose_theme("coko"))
    menu.add_separator()
    menu.add_command(label=("✓ Follow Roblox" if follow_roblox else "Follow Roblox"),
                     command=toggle_follow)
    menu.add_cascade(label="Roblox position", menu=make_position_menu(menu))
    menu.add_separator()
    for value in (1, 30, 60, 100):
        menu.add_command(label=f"CPS {value}", command=lambda v=value: set_cps(v))
    menu.add_separator()
    menu.add_command(label="Reset position", command=reset_position)
    menu.add_command(label="Exit", command=close_app)
    try:
        menu.tk_popup(root.winfo_pointerx(), root.winfo_pointery())
    finally:
        menu.grab_release()


def reset_position():
    global follow_roblox, follow_preset
    follow_roblox, follow_preset = True, "bottom-right"
    rect = get_window_rect(find_roblox())
    if rect:
        position_relative(rect)
    save_settings()


def close_app():
    save_settings()
    root.destroy()


load_settings()

root = tk.Tk()
root.title("GraceRosaryBoost")
root.geometry(f"{W}x{H}+100+100")
root.overrideredirect(True)
root.configure(bg=THEMES[current_theme]["bg"], highlightthickness=2,
               highlightbackground=THEMES[current_theme]["border"])
try:
    root.iconbitmap("icon.ico")
except Exception:
    pass

rain_canvas = tk.Canvas(root, width=W, height=H, bg=THEMES[current_theme]["bg"], highlightthickness=0)
rain_canvas.pack()
rain_canvas.bind("<Button-1>", on_canvas_click)
rain_canvas.bind("<ButtonPress-1>", start_drag)
rain_canvas.bind("<B1-Motion>", drag_window)
rain_canvas.bind("<ButtonRelease-1>", stop_drag)
rain_canvas.bind("<Button-3>", show_menu)
root.bind("<Key>", on_key)
root.bind("<Button-3>", show_menu)

create_rain()

title_text = rain_canvas.create_text(W // 2, 45, text="GrRB", fill="#333333", font=("Impact", 28))
cps_display = rain_canvas.create_text(W // 2, 115, text=cps_value, fill="#333333", font=("Impact", 56))
m4_text = rain_canvas.create_text(70, 185, text="M4", fill="#222222", font=("Impact", 16))
m5_text = rain_canvas.create_text(150, 185, text="M5", fill="#ff0000", font=("Impact", 16))

close_button = tk.Button(root, text="×", bg=THEMES[current_theme]["bg"], fg=THEMES[current_theme]["dim"],
                         bd=0, command=close_app, font=("Arial", 10), relief="flat")
close_button.place(x=W - 20, y=5)
menu_button = tk.Button(root, text="⋮", bg=THEMES[current_theme]["bg"], fg=THEMES[current_theme]["dim"],
                        bd=0, command=show_menu, font=("Arial", 10), relief="flat")
menu_button.place(x=5, y=5)

for widget in (close_button, menu_button):
    widget.bind("<Button-3>", show_menu)

apply_theme()

if saved_x is not None and saved_y is not None and not follow_roblox:
    root.geometry(f"{W}x{H}+{int(saved_x)}+{int(saved_y)}")
else:
    rect = get_window_rect(find_roblox())
    if rect:
        position_relative(rect)
    elif saved_x is not None and saved_y is not None:
        root.geometry(f"{W}x{H}+{int(saved_x)}+{int(saved_y)}")

threading.Thread(target=spam_loop, daemon=True).start()
mouse.Listener(on_click=on_mouse_click).start()
root.after(100, follow_roblox_loop)
root.after(40, attack_visuals)
root.after(35, animate_rain)
root.protocol("WM_DELETE_WINDOW", close_app)
root.mainloop()
