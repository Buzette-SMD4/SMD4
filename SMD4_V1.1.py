import tkinter as tk
from tkinter import simpledialog, messagebox
import requests
import json
import os
from cryptography.fernet import Fernet
import base64
import hashlib
import subprocess

# Paramètres Firebase
FIREBASE_URL = "https://licencesystem-d76d7-default-rtdb.europe-west1.firebasedatabase.app/valid_keys"
FIREBASE_API_KEY = "AIzaSyBbMcuAwbElEQBkge7m3O025hVRM3rEUhc"
CONFIG_FILE = "licence_config.json"
VERSION_URL = "https://licencesystem-d76d7-default-rtdb.europe-west1.firebasedatabase.app/version.json"
LOCAL_VERSION_FILE = "version.txt"

def get_local_version():
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0"

def check_for_update():
    try:
        response = requests.get(VERSION_URL)
        if response.status_code == 200:
            data = response.json()
            latest = data.get("latest_version")
            url = data.get("download_url")
            changelog = data.get("changelog", "")
            local_version = get_local_version()

            if latest and latest > local_version:
                if messagebox.askyesno("🆕 Mise à jour disponible",
                    f"Nouvelle version : {latest}\n\nChangelog :\n{changelog}\n\nSouhaitez-vous la télécharger maintenant ?"):
                    download_and_update(url)
        else:
            print("Erreur Firebase (version).")
    except Exception as e:
        print(f"Erreur lors de la vérification de mise à jour : {e}")
        print(f"Version locale : {local_version} / Version en ligne : {latest}")

def download_and_update(url):
    import webbrowser
    try:
        webbrowser.open(url)
        messagebox.showinfo("Téléchargement", "Le téléchargement a été lancé dans votre navigateur.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec du téléchargement : {e}")

# Lire l'UUID machine depuis wmic (Windows uniquement)
def get_machine_uuid():
    try:
        output = subprocess.check_output("wmic csproduct get uuid", shell=True)
        lines = output.decode().splitlines()
        uuid = [line.strip() for line in lines if line.strip() and line.strip() != "UUID"]
        if uuid:
            return uuid[0]
    except Exception as e:
        print("Erreur récupération UUID:", e)
    return "default-machine-id"

# Dériver la clé depuis l'UUID machine
def derive_key_from_machine():
    uuid = get_machine_uuid()
    sha = hashlib.sha256(uuid.encode()).digest()
    return base64.urlsafe_b64encode(sha)

def get_cipher():
    key = derive_key_from_machine()
    return Fernet(key)

# Obtenir un id_token anonyme
def get_firebase_id_token(api_key):
    try:
        response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}",
            json={"returnSecureToken": True}
        )
        if response.status_code == 200:
            return response.json().get("idToken")
    except Exception as e:
        print("Erreur d'authentification Firebase:", e)
    return None

# Vérifier une clé dans Firebase
def check_license_key(key, username, token):
    try:
        url = f"{FIREBASE_URL}/{key}.json"
        params = {"auth": token}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("user", "").lower() == username.lower():
                return True
    except Exception as e:
        print("Erreur de requête Firebase:", e)
    return False

# Boîte de dialogue personnalisée pour saisir utilisateur + clé
class LicenseDialog:
    def __init__(self, parent):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Validation de licence")
        self.top.geometry("300x150")
        self.top.grab_set()

        tk.Label(self.top, text="Nom d'utilisateur :").pack(pady=(10, 0))
        self.entry_user = tk.Entry(self.top)
        self.entry_user.pack(pady=5)

        tk.Label(self.top, text="Clé de licence :").pack()
        self.entry_key = tk.Entry(self.top, show='*')
        self.entry_key.pack(pady=5)

        tk.Button(self.top, text="Valider", command=self.validate).pack(pady=10)
        self.entry_user.focus()

        self.top.bind("<Return>", lambda event: self.validate())

    def validate(self):
        user = self.entry_user.get().strip()
        key = self.entry_key.get().strip()
        if user and key:
            self.result = (user, key)
            self.top.destroy()
        else:
            messagebox.showwarning("Champs requis", "Veuillez remplir les deux champs.")

# Sauvegarder les infos localement (chiffrées)
def save_license_locally(username, key):
    cipher = get_cipher()
    encrypted_data = {
        "user": cipher.encrypt(username.encode()).decode(),
        "key": cipher.encrypt(key.encode()).decode()
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(encrypted_data, f)

# Charger une licence sauvegardée (déchiffrée)
def load_saved_license():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                encrypted = json.load(f)
            cipher = get_cipher()
            user = cipher.decrypt(encrypted.get("user", "").encode()).decode()
            key = cipher.decrypt(encrypted.get("key", "").encode()).decode()
            return user, key
        except Exception as e:
            print("Erreur de déchiffrement ou lecture config:", e)
    return None, None

import tkinter as tk
import os
from tkinter import messagebox, filedialog, simpledialog, ttk
from PIL import Image, ImageTk
from functools import partial
from PIL import ImageDraw
import json
import threading
import time
from first_launch_wizard import FirstLaunchWizard

def log_key(key_name):
    if "key_log" in globals():
        timestamp = time.strftime("%H:%M:%S")
        key_log.config(state="normal")
        key_log.insert("end", f"[{timestamp}] → {key_name}\n")
        key_log.see("end")
        key_log.config(state="disabled")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] → {key_name}")

import pyautogui
import keyboard
import winsound
import subprocess

custom_visible = False

key_press_lock = threading.Lock()


CROSS_IMAGE_PATH = "red_cross_overlay.png"
if not os.path.exists(CROSS_IMAGE_PATH):
    # Génère une croix rouge transparente (90x90)
    cross = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cross)
    draw.line((10, 10, 80, 80), fill=(255, 0, 0, 200), width=10)
    draw.line((80, 10, 10, 80), fill=(255, 0, 0, 200), width=10)
    cross.save(CROSS_IMAGE_PATH)

root = tk.Tk()
root.withdraw()  # Cache la fenêtre principale pendant la vérification

token = get_firebase_id_token(FIREBASE_API_KEY)
if not token:
    messagebox.showerror("Erreur", "Impossible d'obtenir le token Firebase.")
    root.destroy()
    exit()

saved_user, saved_key = load_saved_license()
if saved_user and saved_key:
    if check_license_key(saved_key, saved_user, token):
        print(f"[LICENCE] Licence valide pour {saved_user} (local)")
        root.deiconify()
        check_for_update()
    else:
        os.remove(CONFIG_FILE)
else:
    dlg = LicenseDialog(root)
    root.wait_window(dlg.top)

    if not dlg.result:
        messagebox.showwarning("Licence", "Licence requise pour utiliser ce logiciel.")
        root.destroy()
        exit()

    username, license_key = dlg.result
    if check_license_key(license_key, username, token):
        save_license_locally(username, license_key)
        messagebox.showinfo("Licence", f"Clé valide. Bienvenue {username} !")
        root.deiconify()
    else:
        messagebox.showerror("Licence invalide", "Clé incorrecte ou utilisateur non autorisé.")
        root.destroy()
        exit()



# === Configuration du mode réduit avec bouton dans Vue d'ensemble ===
window_expanded = True
previous_geometry = ""
btn_restore = None
drag_area = None
restore_frame = None
vertical_frame = None


previous_geometry = ""
btn_restore = None  # Bouton temporaire
drag_area = None


root.title("Macro Sorcier - Icône par défaut intégrée")
root.configure(bg="#444444")

space_spam_enabled_var = tk.BooleanVar(value=True)
shift_click_enabled_var = tk.BooleanVar(value=True)
space_spam_enabled_var = tk.BooleanVar(value=True)
shift_click_enabled_var = tk.BooleanVar(value=True)


entries = []
icons = []
icon_labels = []
dragged_index = None

# Onglets
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

empty_tab = tk.Frame(notebook, bg="#444444")

window_expanded = True
previous_geometry = ""
btn_restore = None
drag_area = None
restore_frame = None
vertical_frame = None
move_bar = None

def toggle_window_mode():
    global window_expanded, previous_geometry, btn_restore, drag_area, restore_frame, vertical_frame, move_bar

    if window_expanded:
        previous_geometry = root.geometry()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry(f"60x470+{root.winfo_screenwidth()-60}+100")

        for widget in root.winfo_children():
            widget.pack_forget()

        drag_area = tk.Frame(root, bg="#333333")
        drag_area.pack(fill="both", expand=True)

        # Barre de déplacement
        move_bar = tk.Frame(drag_area, bg="#333333", height=10, cursor="fleur")
        move_bar.pack(fill="x")

        def start_move(event):
            root._drag_start_x = event.x
            root._drag_start_y = event.y

        def do_move(event):
            x = root.winfo_pointerx() - root._drag_start_x
            y = root.winfo_pointery() - root._drag_start_y
            root.geometry(f"+{x}+{y}")

        move_bar.bind("<Button-1>", start_move)
        move_bar.bind("<B1-Motion>", do_move)

        # Icônes verticales
        vertical_frame = tk.Frame(drag_area, bg="#333333")
        vertical_frame.pack(pady=10)

        overlay_icon_labels.clear()

        for i in range(6):
            icon_path = entries[i]["icon"]
            if not os.path.exists(icon_path):
                icon_path = DEFAULT_ICON
            try:
                base_img = Image.open(icon_path).convert("RGBA").resize((60, 60), Image.LANCZOS)
                if not entries[i]["enabled"].get():
                    cross_img = Image.open(CROSS_IMAGE_PATH).convert("RGBA").resize((60, 60), Image.LANCZOS)
                    base_img = Image.alpha_composite(base_img, cross_img)
                photo = ImageTk.PhotoImage(base_img)
            except Exception as e:
                print(f"[Overlay] Erreur chargement icône {i+1} :", e)
                photo = None

            icon_label = tk.Label(vertical_frame, image=photo, bg="#333333")
            icon_label.image = photo
            icon_label.pack(pady=2)
            overlay_icon_labels.append(icon_label)

            def on_double_click(e, i=i):
                toggle_sort_enabled(i)
                update_overlay_icons_only()

            icon_label.bind("<Double-Button-1>", on_double_click)

        restore_frame = tk.Frame(drag_area, bg="#333333")
        restore_frame.pack(fill="x", side="bottom")

        btn_restore = tk.Button(restore_frame, text=">>", command=toggle_window_mode,
                                bg="#444444", fg="white")
        btn_restore.pack(padx=5, pady=5)

        reduce_button.pack_forget()
        window_expanded = False

    else:
        if btn_restore:
            btn_restore.destroy()
            btn_restore = None
        if restore_frame:
            restore_frame.destroy()
            restore_frame = None
        if vertical_frame:
            vertical_frame.destroy()
            vertical_frame = None
        if drag_area:
            drag_area.destroy()
            drag_area = None
        if move_bar:
            move_bar.destroy()
            move_bar = None

        root.overrideredirect(False)
        root.attributes("-topmost", False)
        root.update_idletasks()
        root.geometry(previous_geometry)

        for widget in root.winfo_children():
            widget.pack()
        reduce_button.pack(side="bottom", anchor="e", padx=10, pady=10)
        window_expanded = True


reduce_button = tk.Button(empty_tab, text=">>", command=toggle_window_mode, bg="#222222", fg="white")
reduce_button.pack(side="bottom", anchor="e", padx=10, pady=10)

# === Bouton de réduction intégré dans Vue d'ensemble ===
reduce_button.pack(side="bottom", anchor="e", padx=10, pady=10)
reduce_button.pack(side="bottom", anchor="e", padx=10, pady=10)

notebook.add(empty_tab, text="Vue d'ensemble")

main_frame = tk.Frame(notebook, bg="#444444")
notebook.add(main_frame, text="Réglages")

button_frame = tk.Frame(main_frame, bg="#444444")
button_frame.pack(pady=10)

# === Icônes de Vue d'ensemble ===
overview_frame = tk.Frame(empty_tab, bg="#444444")
custom_center_frame = tk.Frame(empty_tab, bg="#444444")
custom_center_frame.place(relx=0.5, rely=0.5, anchor="center")  # centré
overview_frame.pack(pady=20, anchor="n")


# === Gestion des profils ===
CONFIG_FOLDER = "profiles"
DEFAULT_PROFILE = "default"
LAST_PROFILE_FILE = "last_profile.txt"

if not os.path.exists(CONFIG_FOLDER):
    os.makedirs(CONFIG_FOLDER)

if os.path.exists(LAST_PROFILE_FILE):
    try:
        with open(LAST_PROFILE_FILE, "r") as f:
            current_profile = f.read().strip()
    except:
        current_profile = DEFAULT_PROFILE
else:
    current_profile = DEFAULT_PROFILE

def save_last_profile(profile):
    with open(LAST_PROFILE_FILE, "w") as f:
        f.write(profile)



def save_config(sorts=None):
    global current_profile
    if not os.path.exists(CONFIG_FOLDER):
        os.makedirs(CONFIG_FOLDER)
    if sorts is None:
        sorts = []
        print("[MACRO] Lancement avec sorts :", sorts)

        for i in range(6):
            sorts.append({
                "x": int(entries[i]["x"].get()),
                "y": int(entries[i]["y"].get()),
                "color": entries[i]["color"].get(),
                "key": entries[i]["key"].get(),
            "enabled": entries[i]["enabled"].get(),
                "icon": entries[i]["icon"]
            })
    config_data = {
        "sorts": sorts,
        "control_key": control_key_entry.get(),
        "delay": delay_entry.get(),
        "space_delay": space_delay_entry.get(),
        "space_spam_enabled": space_spam_enabled_var.get(),
        "shift_click_enabled": shift_click_enabled_var.get(),
        "click_button": click_button_entry.get()
    }
    with open(get_profile_path(current_profile), "w") as f:
        json.dump(config_data, f, indent=4)
    save_last_profile(current_profile)





def get_profile_path(profile_name):
    return os.path.join(CONFIG_FOLDER, f"{profile_name}.json")

def list_profiles():
    return [f[:-5] for f in os.listdir(CONFIG_FOLDER) if f.endswith(".json")]

DEFAULT_ICON = "default_icon.png"
running = False
control_key = "f10"
delay_ms = 100
space_delay_ms = 50
space_spam_enabled = True
app_active = True
click_button = "left"  # Valeur par défaut

default_sorts = [
    {"x": 865, "y": 1006, "color": "0xC6561A", "key": "num2", "icon": DEFAULT_ICON},
    {"x": 928, "y": 1004, "color": "0x2A84AB", "key": "num3", "icon": DEFAULT_ICON},
    {"x": 988, "y": 1009, "color": "0x292399", "key": "num4", "icon": DEFAULT_ICON},
    {"x": 800, "y": 1000, "color": "0x3A59A8", "key": "num1", "icon": DEFAULT_ICON},
    {"x": 1115, "y": 1006, "color": "0xE4CA9D", "key": "right", "icon": DEFAULT_ICON},
    {"x": 1175, "y": 1008, "color": "0xFFFFFF", "key": "a", "icon": DEFAULT_ICON}
]

def load_config(profile):
    global click_button
    if os.path.exists(get_profile_path(profile)):
        with open(get_profile_path(profile), "r") as f:
            data = json.load(f)
            sorts = data.get("sorts", default_sorts)
            for s in sorts:
                if not s.get("icon"):
                    s["icon"] = DEFAULT_ICON
            click_button = data.get("click_button", "left")
            global space_spam_enabled
            space_spam_enabled = data.get("space_spam_enabled", True)
            shift_click_enabled_default = data.get("shift_click_enabled", True)
            return (
                sorts,
                data.get("control_key", "f10"),
                int(data.get("delay", 100)),
                int(data.get("space_delay", 50))
            )
    return default_sorts, "f10", 100, 50

def hex_to_rgb(hex_color):
    hex_color = hex_color.replace("0x", "")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"0x{r:02X}{g:02X}{b:02X}"

def colors_match(actual, expected, tolerance=10):
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))

def normalize_key(key):
    return key.replace(" ", "").lower()




def reinforce_mouse_hold():
    while running and shift_click_enabled_var.get():
        try:
            pyautogui.mouseDown(button=click_button)
        except Exception as e:
            print(f"[ERREUR] Renforcement clic : {e}")
        time.sleep(0.2)  # Renforce toutes les 200 ms


def spam_space_key():
    while running:
        if space_spam_enabled_var.get():
            try:
                keyboard.send("space")
                log_key("Espace")
            except Exception as e:
                print(f"[ERREUR] Spam espace : {e}")
        time.sleep(space_delay_ms / 1000.0)



def check_and_spam(sorts):
    global running, delay_ms, click_button
    while running:
        for i, sort in enumerate(sorts):
            if not entries[i]["enabled"].get():
                continue
            try:
                px = pyautogui.pixel(sort["x"], sort["y"])
                expected = hex_to_rgb(sort["color"])
                if colors_match(px, expected):
                    key = normalize_key(sort["key"])
                    if key in ["left", "right", "middle"]:
                        pyautogui.click(button=key)
                        log_key(f"Clic souris : {key}")
                    else:
                        pyautogui.press(key)
                        log_key(f"Touche sort : {key}")
                    log_key(f"Touche sort : {key}")
            except Exception:
                pass
        time.sleep(delay_ms / 1000.0)



def toggle_macro():
    global running, sorts, delay_ms, space_delay_ms, control_key
    if running:
        running = False
        winsound.Beep(400, 200)
        if shift_click_enabled_var.get():
            pyautogui.mouseUp(button=click_button)
            log_key(f"Clic {click_button} (relâché)")
            pyautogui.keyUp("shift")
            log_key("Shift (relâché)")
    else:
        sorts = []
        for i in range(6):
            sorts.append({
                "x": int(entries[i]["x"].get()),
                "y": int(entries[i]["y"].get()),
                "color": entries[i]["color"].get(),
                "key": entries[i]["key"].get(),
                "enabled": entries[i]["enabled"].get(),
                "icon": entries[i]["icon"]
            })
        delay_ms = int(delay_entry.get())
        space_delay_ms = int(space_delay_entry.get())
        control_key = control_key_entry.get()
        running = True
        winsound.Beep(400, 200)

        if shift_click_enabled_var.get():
            pyautogui.keyDown("shift")
            log_key("Shift (maintenu)")
            pyautogui.mouseDown(button=click_button)
            log_key(f"Clic {click_button} (maintenu)")

        threading.Thread(target=check_and_spam, args=(sorts,), daemon=True).start()
        threading.Thread(target=reinforce_mouse_hold, daemon=True).start()
        threading.Timer(0.2, lambda: threading.Thread(target=spam_space_key, daemon=True).start()).start()


def change_icon(index):
    classes = [
        ("Barbare", "barbare.png"),
        ("Sorcier", "sorcier.png"),
        ("Voleur", "voleur.png"),
        ("Nécromancien", "nécromancien.png"),
        ("Druide", "druide.png"),
        ("Sacresprit", "sacresprit.png")
    ]

    window = tk.Toplevel(root)
    window.title("Choisis ta classe")
    window.configure(bg="#333333")
    window.geometry("450x300")

    frame = tk.Frame(window, bg="#333333")
    frame.pack(padx=20, pady=20)

    window.class_buttons_images = []

    def handle_click(class_name):
        window.destroy()
        open_icon_selector(class_name, index)

    for i, (class_name, filename) in enumerate(classes):
        path = os.path.join("class_icons", filename)
        try:
            img = Image.open(path).convert("RGBA").resize((64, 64))
            photo = ImageTk.PhotoImage(img)
            window.class_buttons_images.append(photo)  # éviter le garbage collector

            btn = tk.Button(
                frame,
                image=photo,
                text=class_name,
                compound="top",
                command=lambda c=class_name: handle_click(c),
                bg="#444444",
                fg="white",
                font=("Arial", 9),
                width=80,
                height=100
            )
            btn.grid(row=i // 3, column=i % 3, padx=10, pady=10)
        except Exception as e:
            print(f"Erreur chargement icône pour {class_name} : {e}")


def open_icon_selector(selected_class, index):
    class_folder = os.path.join("sorts_icons", selected_class.lower())
    if not os.path.exists(class_folder):
        messagebox.showerror("Erreur", f"Dossier non trouvé : {class_folder}")
        return

    preview_window = tk.Toplevel(root)
    preview_window.title(f"Icônes pour {selected_class}")
    preview_window.configure(bg="#333333")
    preview_window.icon_buttons_images = []

    icons_frame = tk.Frame(preview_window, bg="#333333")
    icons_frame.pack(padx=10, pady=10)

    image_files = [f for f in os.listdir(class_folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    if not image_files:
        messagebox.showerror("Erreur", f"Aucune image trouvée dans {class_folder}")
        preview_window.destroy()
        return

    def select_icon(path):
        entries[index]["icon"] = path
        update_icon(index)
        update_overview_icons()
        preview_window.destroy()

    for i, file in enumerate(image_files):
        full_path = os.path.join(class_folder, file)
        try:
            img = Image.open(full_path).convert("RGBA").resize((64, 64))
            bg = Image.new("RGBA", img.size, (30, 30, 30, 255))
            img = Image.alpha_composite(bg, img)
            photo = ImageTk.PhotoImage(img)
            preview_window.icon_buttons_images.append(photo)

            btn = tk.Button(icons_frame, image=photo, command=lambda p=full_path: select_icon(p))
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
        except Exception as e:
            print(f"[ERREUR Chargement {file}] : {e}")


def update_sort_position(index):
    x_val = entries[index]["x"].get()
    y_val = entries[index]["y"].get()
    test_x.delete(0, "end")
    test_x.insert(0, x_val)
    test_y.delete(0, "end")
    test_y.insert(0, y_val)

def test_color():
    try:
        x = int(test_x.get())
        y = int(test_y.get())
        px = pyautogui.pixel(x, y)
        result_label.config(text=f"Couleur à ({x},{y}) = RGB{px}")
    except Exception as e:
        result_label.config(text=f"Erreur : {e}")

def convert_rgb_to_hex():
    try:
        rgb = result_label.cget("text")
        if "RGB" in rgb:
            parts = rgb.split("RGB")[1].strip("()").split(",")
            r, g, b = map(int, parts)
            hex_value = rgb_to_hex(r, g, b)
            hex_output_label.config(text=f"→ {hex_value}")
    except:
        hex_output_label.config(text="→ Erreur")

def copy_hex_to_clipboard():
    hex_val = hex_output_label.cget("text").replace("→", "").strip()
    if hex_val:
        root.clipboard_clear()
        root.clipboard_append(hex_val)
        root.update()

def monitor_control_key():
    global control_key, app_active
    while app_active:
        try:
            if keyboard.is_pressed(control_key):
                toggle_macro()
                time.sleep(0.5)
        except:
            pass
        time.sleep(0.1)

def monitor_capture_key():
    global app_active
    while app_active:
        try:
            if keyboard.is_pressed("f8"):
                x, y = pyautogui.position()
                captured_coords_var.set(f"{x}, {y}")
                time.sleep(0.5)
        except:
            pass
        time.sleep(0.1)

def update_all_colors_from_pixels():
    updated = 0
    try:
        root.withdraw()
        time.sleep(0.8)  # Allonge le temps pour être sûr que l'interface disparaisse et que le jeu ait le temps de s'afficher

        for i in range(len(entries)):
            try:
                x = int(entries[i]["x"].get())
                y = int(entries[i]["y"].get())

                print(f"[DEBUG] Capture couleur sort {i+1} à ({x}, {y})...")  # log

                rgb = pyautogui.pixel(x, y)
                hex_color = rgb_to_hex(*rgb)
                entries[i]["color"].delete(0, tk.END)
                entries[i]["color"].insert(0, hex_color)
                updated += 1
                print(f"[MAJ] Sort {i+1} : {hex_color}")
            except Exception as e:
                print(f"[ERREUR MAJ couleur sort {i+1}] : {e}")
    finally:
        root.deiconify()
        update_overview_icons()
        restore_special_buttons()

def toggle_space_spam():
    global space_spam_enabled
    space_spam_enabled = not space_spam_enabled
    state = 'activé' if space_spam_enabled else 'désactivé'
    messagebox.showinfo('Spam espace', f'Spam espace {state}')

def on_close():
    global running, app_active
    running = False
    app_active = False
    root.destroy()


sorts, control_key, delay_ms, space_delay_ms = load_config(current_profile)

for i in range(6):
    frame = tk.LabelFrame(main_frame, bg="#444444", fg="white")
    frame.pack(padx=10, pady=5, fill="x")

    icon_path = sorts[i].get("icon", DEFAULT_ICON)
    if not os.path.exists(icon_path):
        icon_path = DEFAULT_ICON

    try:
        img = Image.open(icon_path).resize((24, 24))
        photo = ImageTk.PhotoImage(img)
    except:
        photo = None
    icons.append(photo)

    icon_label = tk.Label(frame, image=photo, bg="#444444")
    icon_label.pack(side="left", padx=2)
    icon_label.bind("<Button-1>", lambda e, i=i: change_icon(i))
    icon_labels.append(icon_label)

    enabled = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, variable=enabled, bg="#444444").pack(side="left", padx=2)

    sort_btn = tk.Button(frame, text=f"Sort {i+1}", bg="#333333", fg="white", command=lambda i=i: update_sort_position(i))
    sort_btn.pack(side="left", padx=2)

    x_entry = tk.Entry(frame, width=6)
    x_entry.insert(0, sorts[i]["x"])
    x_entry.pack(side="left", padx=2)

    y_entry = tk.Entry(frame, width=6)
    y_entry.insert(0, sorts[i]["y"])
    y_entry.pack(side="left", padx=2)

    color_entry = tk.Entry(frame, width=10)
    color_entry.insert(0, sorts[i]["color"])
    color_entry.pack(side="left", padx=2)

    key_entry = tk.Entry(frame, width=10)
    key_entry.insert(0, sorts[i]["key"])
    key_entry.pack(side="left", padx=2)

    entries.append({
        "x": x_entry,
        "y": y_entry,
        "color": color_entry,
        "key": key_entry,
        "enabled": enabled,
        "icon": icon_path
    })

# === Vue d'ensemble : création des carrés avec les icônes ===
overview_frame = tk.Frame(empty_tab, bg="#444444")
overview_frame.pack(pady=5)

row_frame = tk.Frame(overview_frame, bg="#444444")
row_frame.pack()



# Frame pour les deux boutons
special_buttons_frame = tk.Frame(overview_frame, bg="#444444")
special_buttons_frame.pack(pady=5)

# Chargement des 4 images de boutons
try:
    space_on_img = ImageTk.PhotoImage(Image.open("btn_space_on.png").resize((180, 180), Image.LANCZOS))
    space_off_img = ImageTk.PhotoImage(Image.open("btn_space_off.png").resize((180, 180), Image.LANCZOS))
    shift_on_img = ImageTk.PhotoImage(Image.open("btn_shift_on.png").resize((180, 180), Image.LANCZOS))
    shift_off_img = ImageTk.PhotoImage(Image.open("btn_shift_off.png").resize((180, 180), Image.LANCZOS))
    farm_img = ImageTk.PhotoImage(Image.open("farm_pit.png").resize((180, 180), Image.LANCZOS))
    custom_img = ImageTk.PhotoImage(Image.open("btn_custom.png").resize((180, 180), Image.LANCZOS))
    profile_img = ImageTk.PhotoImage(Image.open("btn_profile.png").resize((180, 180), Image.LANCZOS))


except Exception as e:
    print("[ERREUR] Chargement image bouton :", e)

farm_mode_enabled_var = tk.BooleanVar(value=False)

def restore_custom_button():
    btn_custom.configure(image=custom_img)
    btn_custom.image = custom_img

# Fonction pour actualiser les images
def update_special_buttons():
    btn_space.configure(image=space_on_img if space_spam_enabled_var.get() else space_off_img)
    btn_space.image = space_on_img if space_spam_enabled_var.get() else space_off_img

    btn_shift.configure(image=shift_on_img if shift_click_enabled_var.get() else shift_off_img)
    btn_shift.image = shift_on_img if shift_click_enabled_var.get() else shift_off_img

# Fonction toggle mise à jour
def toggle_space_from_overview():
    space_spam_enabled_var.set(not space_spam_enabled_var.get())
    update_special_buttons()
    update_overview_icons()

def toggle_shift_from_overview():
    shift_click_enabled_var.set(not shift_click_enabled_var.get())
    update_special_buttons()
    update_overview_icons()

def toggle_farm_mode():
    farm_mode_enabled_var.set(not farm_mode_enabled_var.get())
    state = "ACTIVÉ" if farm_mode_enabled_var.get() else "DÉSACTIVÉ"
    messagebox.showinfo("Farm Pit", f"Mode Farm Pit {state}")

import subprocess
import sys

def launch_timer_app():
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # Masquer la console

        subprocess.Popen(
            [sys.executable, "Minuteurs.py"],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de lancer le minuteur : {e}")

try:
    timer_img = ImageTk.PhotoImage(Image.open("btn_timer.png").resize((180, 180), Image.LANCZOS))
except Exception as e:
    print("[ERREUR] Chargement bouton timer :", e)
       

def launch_farm_pit_tracker():
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # Masquer la console

        subprocess.Popen(
            [sys.executable, "xp_tracker_pit_gui_SAFE.py"],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de lancer le tracker Pit : {e}")
    
def open_profile_selector():
    selector = tk.Toplevel(root)
    selector.title("Choisir un profil")
    selector.configure(bg="#333333")

    # Centrage et agrandissement
    selector.update_idletasks()
    width = 300
    height = 300
    x = (selector.winfo_screenwidth() // 2) - (width // 2)
    y = (selector.winfo_screenheight() // 2) - (height // 2)
    selector.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(selector, text="Sélectionne un profil :", bg="#333333", fg="white", font=("Arial", 12)).pack(pady=10)

    for prof in list_profiles():
        tk.Button(
            selector, text=prof,
            command=lambda p=prof: (profile_var.set(p), selector.destroy()),
            bg="#555555", fg="white", width=20
        ).pack(pady=2)

    tk.Button(selector, text="Annuler", command=selector.destroy, bg="#666666", fg="white").pack(pady=10)

# === Conteneur principal des boutons spéciaux ===
special_buttons_frame = tk.Frame(overview_frame, bg="#444444")
special_buttons_frame.pack(pady=20)

# --- Ligne 1 : MAJ SORT (centré au-dessus)
btn_custom = tk.Button(custom_center_frame, bd=0, relief="flat", bg="#444444",
                       image=custom_img, command=update_all_colors_from_pixels,
                       activebackground="#444444")
btn_custom.image = custom_img
# btn_custom.pack(pady=(0, 10))  # Marge en bas
btn_custom.pack_forget()  # 👈 pour le cacher au lancement

bottom_buttons_frame = tk.Frame(special_buttons_frame, bg="#444444")
bottom_buttons_frame.pack()

third_buttons_frame = tk.Frame(special_buttons_frame, bg="#444444")
third_buttons_frame.pack()


btn_profile = tk.Button(third_buttons_frame, bd=0, relief="flat", bg="#444444",
                        image=profile_img, command=open_profile_selector,
                        activebackground="#444444")
btn_profile.image = profile_img
btn_profile.grid(row=0, column=0, padx=10, pady=10)


btn_shift = tk.Button(bottom_buttons_frame, bd=0, relief="flat", bg="#444444",
                      image=shift_on_img, command=toggle_shift_from_overview,
                      activebackground="#444444")
btn_shift.grid(row=0, column=0, padx=10, pady=10)

btn_space = tk.Button(bottom_buttons_frame, bd=0, relief="flat", bg="#444444",
                      image=space_on_img, command=toggle_space_from_overview,
                      activebackground="#444444")
btn_space.grid(row=0, column=1, padx=10, pady=10)

btn_farm = tk.Button(bottom_buttons_frame, bd=0, relief="flat", bg="#444444",
                     image=farm_img, command=launch_farm_pit_tracker,
                     activebackground="#444444")
btn_farm.grid(row=1, column=0, padx=10, pady=10)

btn_timer = tk.Button(bottom_buttons_frame, bd=0, relief="flat", bg="#444444",
                      image=timer_img if 'timer_img' in globals() else None,
                      command=launch_timer_app, activebackground="#444444",
                      fg="white", font=("Arial", 10))
btn_timer.grid(row=1, column=1, padx=10, pady=10)


def show_only_btn_custom():
    global custom_visible
    if not custom_visible:
        btn_shift.grid_remove()
        btn_space.grid_remove()
        btn_farm.grid_remove()
        btn_timer.grid_remove()
        btn_profile.grid_remove()


        custom_center_frame.place(relx=0.5, rely=0.5, anchor="center")
        btn_custom.pack(pady=10)
        btn_custom.configure(image=custom_img)
        btn_custom.image = custom_img
        custom_center_frame.lift()
        root.update_idletasks()
        custom_visible = True


def restore_special_buttons():
    global custom_visible
    btn_custom.pack_forget()
    custom_center_frame.place_forget()
    btn_shift.grid(row=0, column=0, padx=10, pady=10)
    btn_space.grid(row=0, column=1, padx=10, pady=10)
    btn_farm.grid(row=1, column=0, padx=10, pady=10)
    btn_timer.grid(row=1, column=1, padx=10, pady=10)
    btn_profile.grid(row=0, column=0, padx=10, pady=10)


    custom_visible = False

# Initialisation des bonnes images
update_special_buttons()

def toggle_space_from_overview():
    space_spam_enabled_var.set(not space_spam_enabled_var.get())
    update_overview_icons()

def toggle_shift_from_overview():
    shift_click_enabled_var.set(not shift_click_enabled_var.get())
    update_overview_icons()

overview_boxes = []
overview_icons = []
overlay_icon_labels = []

dragged_index = None

def on_start_drag(event, idx):
    global dragged_index
    dragged_index = idx
    print(f"[START DRAG] Index = {idx}")

def on_drag_motion(event):
    # Permet le suivi du drag
    pass

def on_drop(event):
    global dragged_index
    if dragged_index is None:
        return

    x_root, y_root = event.x_root, event.y_root
    widget_under_cursor = root.winfo_containing(x_root, y_root)

    target_index = None
    for i, box in enumerate(overview_boxes):
        if widget_under_cursor in box.winfo_children() or widget_under_cursor == box:
            target_index = i
            break

    if target_index is not None and target_index != dragged_index:
       print(f"[DROP] De {dragged_index} vers {target_index}")
       swap_sorts(dragged_index, target_index)
       show_only_btn_custom()  # flash appelé qu’une seule fois

    else:
        print(f"[DROP] Aucun changement (vers {target_index})")

    dragged_index = None

import time

def log_key(key_name):
    if "key_log" in globals():
        timestamp = time.strftime("%H:%M:%S")
        key_log.config(state="normal")
        key_log.insert("end", f"[{timestamp}] → {key_name}\n")
        key_log.see("end")
        key_log.config(state="disabled")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] → {key_name}")

def log_key(key_name):
    if "key_log" in globals():
        timestamp = time.strftime("%H:%M:%S")
        key_log.config(state="normal")
        key_log.insert("end", f"[{timestamp}] → {key_name}\n")
        key_log.see("end")
        key_log.config(state="disabled")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] → {key_name}")

def swap_sorts(i, j):
    try:
        # Récupère les données actuelles des deux sorts
        sort_i = {
            "x": entries[i]["x"].get(),
            "y": entries[i]["y"].get(),
            "color": entries[i]["color"].get(),
            "key": entries[i]["key"].get(),
            "enabled": entries[i]["enabled"].get(),
            "icon": entries[i]["icon"]
        }

        sort_j = {
            "x": entries[j]["x"].get(),
            "y": entries[j]["y"].get(),
            "color": entries[j]["color"].get(),
            "key": entries[j]["key"].get(),
            "enabled": entries[j]["enabled"].get(),
            "icon": entries[j]["icon"]
        }

        # Échange les données
        for field in ["x", "y", "color", "key"]:
            entries[i][field].delete(0, tk.END)
            entries[i][field].insert(0, sort_j[field])

            entries[j][field].delete(0, tk.END)
            entries[j][field].insert(0, sort_i[field])

        entries[i]["enabled"].set(sort_j["enabled"])
        entries[j]["enabled"].set(sort_i["enabled"])

        entries[i]["icon"] = sort_j["icon"]
        entries[j]["icon"] = sort_i["icon"]

        # Mettre à jour les icônes et la vue
        update_icon(i)
        update_icon(j)
        update_overview_icons()

        # Sauvegarde la nouvelle config
        save_config()

    except Exception as e:
        print(f"[Swap] Erreur pendant le drag & drop : {e}")


def update_overview_icons():
    for i in range(6):
        if i >= len(overview_boxes):
            continue  # Protection si la box n'existe pas encore

        # Supprime les anciens widgets dans la box
        for widget in overview_boxes[i].winfo_children():
            widget.destroy()

        icon_path = entries[i]["icon"]
        if not os.path.exists(icon_path):
            icon_path = DEFAULT_ICON

        try:
            base_img = Image.open(icon_path).convert("RGBA").resize((90, 90), Image.LANCZOS)
            if not entries[i]["enabled"].get():
                cross_img = Image.open(CROSS_IMAGE_PATH).convert("RGBA").resize((90, 90), Image.LANCZOS)
                base_img = Image.alpha_composite(base_img, cross_img)
            photo = ImageTk.PhotoImage(base_img)
        except Exception as e:
            print(f"Erreur image sort {i+1} : {e}")
            photo = None

        overview_icons[i] = photo

        label = tk.Label(overview_boxes[i], image=photo, bg="#666666")
        label.place(relx=0.5, rely=0.5, anchor="center")
        label.bind("<ButtonPress-1>", lambda e, i=i: on_start_drag(e, i))
        label.bind("<B1-Motion>", on_drag_motion)
        label.bind("<ButtonRelease-1>", on_drop)
        label.bind("<Double-Button-1>", lambda e, i=i: toggle_sort_enabled(i))

def toggle_sort_enabled(index):
    current_state = entries[index]["enabled"].get()
    entries[index]["enabled"].set(not current_state)
    update_overview_icons()

def create_overview_icons():
    for widget in row_frame.winfo_children():
        widget.destroy()
    overview_boxes.clear()
    overview_icons.clear()


    for i in range(6):
        box = tk.Frame(row_frame, width=100, height=100, bg="#666666", relief="ridge", borderwidth=2)
        box.pack(side="left", padx=10)

        icon_path = entries[i]["icon"]
        if not os.path.exists(icon_path):
            icon_path = DEFAULT_ICON
        try:
            img = Image.open(icon_path).convert("RGBA")
            img = img.resize((90, 90), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Erreur image sort {i+1} : {e}")
            photo = None

        overview_icons.append(photo)

        label = tk.Label(box, image=photo, bg="#666666")
        label.place(relx=0.5, rely=0.5, anchor="center")

            # DRAG AND DROP avec lambdas pour capturer l’index
        label.bind("<ButtonPress-1>", lambda e, i=i: on_start_drag(e, i))
        label.bind("<ButtonRelease-1>", lambda e, i=i: on_drop(e, i))


        overview_boxes.append(box)
        print("Création des icônes : drag bindé pour", i)

      # ... définition de la fonction create_overview_icons() ...

create_overview_icons()  # ✅ Appelle juste ici

update_overview_icons()  # ✅ Ensuite tu mets à jour ce qui est affiché




# Reste de l'interface
config_frame = tk.Frame(main_frame, bg="#444444")
config_frame.pack(pady=10)
tk.Label(config_frame, text="Touche Démarrage/Arrêt :", bg="#444444", fg="white").pack(side="left")
control_key_entry = tk.Entry(config_frame, width=8)
control_key_entry.insert(0, control_key)
control_key_entry.pack(side="left", padx=5)

tk.Label(config_frame, text="Touche Clic (left/right/middle) :", bg="#444444", fg="white").pack(side="left")
click_button_entry = tk.Entry(config_frame, width=8)
click_button_entry.insert(0, click_button)
click_button_entry.pack(side="left", padx=5)

tk.Label(config_frame, text="Délai général (ms) :", bg="#444444", fg="white").pack(side="left")
delay_entry = tk.Entry(config_frame, width=6)
delay_entry.insert(0, str(delay_ms))
delay_entry.pack(side="left", padx=5)

tk.Label(config_frame, text="Délai espace (ms) :", bg="#444444", fg="white").pack(side="left")
space_delay_entry = tk.Entry(config_frame, width=6)
space_delay_entry.insert(0, str(space_delay_ms))
space_delay_entry.pack(side="left", padx=5)
space_spam_enabled_var.set(space_spam_enabled)
tk.Checkbutton(button_frame, text="Activer Spam Espace", variable=space_spam_enabled_var).pack(side="left", padx=5)
shift_click_enabled_var = tk.BooleanVar()
shift_click_enabled_var.set(True)
tk.Checkbutton(button_frame, text="Activer Shift + Clic", variable=shift_click_enabled_var).pack(side="left", padx=5)
tk.Button(button_frame, text="Démarrer / Arrêter Macro", command=toggle_macro).pack(side="left", padx=5)
space_spam_enabled_var.trace_add("write", lambda *args: update_special_buttons())
shift_click_enabled_var.trace_add("write", lambda *args: update_special_buttons())


def update_shift_state():
    global shift_click_enabled
    shift_click_enabled = shift_click_enabled_var.get()

shift_click_enabled_var.trace_add("write", lambda *args: update_shift_state())
update_shift_state()

tk.Button(button_frame, text="Sauvegarder", command=lambda: save_config(sorts)).pack(side="left", padx=5)

test_frame = tk.Frame(main_frame, bg="#444444")
test_frame.pack(pady=(10, 5))
tk.Label(test_frame, text="X:", bg="#444444", fg="white").pack(side="left")
test_x = tk.Entry(test_frame, width=6)
test_x.pack(side="left", padx=5)
tk.Label(test_frame, text="Y:", bg="#444444", fg="white").pack(side="left")
test_y = tk.Entry(test_frame, width=6)
test_y.pack(side="left", padx=5)
tk.Button(test_frame, text="Tester couleur", command=test_color).pack(side="left", padx=5)

result_label = tk.Label(main_frame, text="", bg="#444444", fg="white")
result_label.pack()
tk.Button(main_frame, text="Convertir en 0x...", command=convert_rgb_to_hex).pack(pady=2)
hex_output_label = tk.Label(main_frame, text="", bg="#444444", fg="white")
hex_output_label.pack()
tk.Button(main_frame, text="Copier la couleur", command=copy_hex_to_clipboard).pack(pady=2)

capture_frame = tk.Frame(main_frame, bg="#444444")
capture_frame.pack(pady=(10, 5))
tk.Label(capture_frame, text="Coordonnées capturées (F8) :", bg="#444444", fg="white").pack(side="left")
captured_coords_var = tk.StringVar()
captured_coords_entry = tk.Entry(capture_frame, textvariable=captured_coords_var, width=20)
captured_coords_entry.pack(side="left", padx=5)

threading.Thread(target=monitor_control_key, daemon=True).start()
threading.Thread(target=monitor_capture_key, daemon=True).start()
root.protocol("WM_DELETE_WINDOW", on_close)



def update_icon(index):
    try:
        icon_path = entries[index]["icon"]
        if not os.path.exists(icon_path):
            raise FileNotFoundError(f"Fichier introuvable : {icon_path}")
        img = Image.open(icon_path).resize((24, 24))
        photo = ImageTk.PhotoImage(img)
        icons[index] = photo
        icon_labels[index].configure(image=photo)
    except Exception as e:
        print(f"Erreur lors de la mise à jour de l'icône du sort {index+1} : {e}")
        icons[index] = None
        icon_labels[index].configure(image='', text='🧪')

    update_overview_icons()

def change_profile(value):
    global current_profile, control_key, delay_ms, space_delay_ms, space_spam_enabled, shift_click_enabled, sorts

    current_profile = value
    save_last_profile(current_profile)

    try:
        with open(get_profile_path(current_profile), "r") as f:
            cfg = json.load(f)

        loaded_sorts = cfg.get("sorts", default_sorts)
        sorts = []  # Met à jour la variable globale utilisée par la boucle

        for i, sort in enumerate(loaded_sorts):
            update_overview_icons()

            entries[i]["x"].delete(0, tk.END)
            entries[i]["x"].insert(0, sort.get("x", 0))
            entries[i]["y"].delete(0, tk.END)
            entries[i]["y"].insert(0, sort.get("y", 0))
            entries[i]["color"].delete(0, tk.END)
            entries[i]["color"].insert(0, sort.get("color", ""))
            entries[i]["key"].delete(0, tk.END)
            entries[i]["key"].insert(0, sort.get("key", ""))
            entries[i]["enabled"].set(sort.get("enabled", False))
            entries[i]["icon"] = sort.get("icon", DEFAULT_ICON)
            update_icon(i)

            # MAJ dans la variable utilisée par la boucle
            sorts.append({
                "x": sort.get("x", 0),
                "y": sort.get("y", 0),
                "color": sort.get("color", ""),
                "key": sort.get("key", ""),
                "enabled": sort.get("enabled", False),
                "icon": sort.get("icon", DEFAULT_ICON)
            
            })
            
            
        # Mise à jour des options générales
        control_key_entry.delete(0, tk.END)
        control_key_entry.insert(0, cfg.get("control_key", "f10"))
        delay_entry.delete(0, tk.END)
        delay_entry.insert(0, str(cfg.get("delay", 100)))
        space_delay_entry.delete(0, tk.END)
        space_delay_entry.insert(0, str(cfg.get("space_delay", 50)))
        space_spam_enabled_var.set(cfg.get("space_spam_enabled", False))
        shift_click_enabled_var.set(cfg.get("shift_click_enabled", False))
        click_button_entry.delete(0, tk.END)
        click_button_entry.insert(0, cfg.get("click_button", "left"))

        update_overview_icons()  # 👈 Redessine les icônes avec le bon drag & drop actif

    except Exception as e:
        print(f"Erreur lors du chargement du profil : {e}")



def save_as_new_profile():
    global current_profile
    new_name = simpledialog.askstring("Nouveau profil", "Nom du nouveau profil :")
    if new_name:
        current_profile = new_name
        profile_var.set(new_name)
        save_config(sorts)
        refresh_profiles()
        profile_var.set(new_name)
        change_profile()

def delete_current_profile():
    global current_profile
    profile = profile_var.get()
    if profile == DEFAULT_PROFILE:
        messagebox.showwarning("Erreur", "Impossible de supprimer le profil par défaut.")
        return
    if messagebox.askyesno("Supprimer", f"Supprimer le profil '{profile}' ?"):
        os.remove(get_profile_path(profile))
        current_profile = DEFAULT_PROFILE
        profile_var.set(DEFAULT_PROFILE)
        refresh_profiles()
        change_profile()

def refresh_profiles():
    menu = profile_menu["menu"]
    menu.delete(0, "end")
    for p in list_profiles():
        menu.add_command(label=p, command=tk._setit(profile_var, p, change_profile))


# ==== GUI PROFIL ====
profile_frame = tk.Frame(main_frame, bg="#444444")
profile_frame.pack(pady=10)
tk.Label(profile_frame, text="Profil :", bg="#444444", fg="white").pack(side="left")
profile_var = tk.StringVar(value=current_profile)
profile_menu = tk.OptionMenu(profile_frame, profile_var, current_profile, *list_profiles())
profile_menu.pack(side="left", padx=5)

update_btn = tk.Button(profile_frame, text="💾 Mettre à jour le profil", command=save_config)
update_btn.pack(side=tk.LEFT, padx=5)

tk.Button(profile_frame, text="Sauver sous...", command=save_as_new_profile).pack(side="left", padx=5)
tk.Button(profile_frame, text="Supprimer", command=delete_current_profile).pack(side="left", padx=5)
refresh_profiles()

profile_var.trace_add("write", lambda *args: change_profile(profile_var.get()))

refresh_profiles()

# ==== FIN GUI PROFIL ====

update_overview_icons()

def update_overlay_icons_only():
    for i, icon_label in enumerate(overlay_icon_labels):
        icon_path = entries[i]["icon"]
        if not os.path.exists(icon_path):
            icon_path = DEFAULT_ICON
        try:
            base_img = Image.open(icon_path).convert("RGBA").resize((60, 60), Image.LANCZOS)
            if not entries[i]["enabled"].get():
                cross_img = Image.open(CROSS_IMAGE_PATH).convert("RGBA").resize((60, 60), Image.LANCZOS)
                base_img = Image.alpha_composite(base_img, cross_img)
            photo = ImageTk.PhotoImage(base_img)
            icon_label.configure(image=photo)
            icon_label.image = photo
        except Exception as e:
            print(f"[Overlay Refresh] Erreur chargement icône {i+1} :", e)

# === Affichage des touches envoyées ===
log_frame = tk.Frame(main_frame, bg="#444444")
log_frame.pack(pady=(10, 5))

tk.Label(log_frame, text="Historique des touches envoyées :", bg="#444444", fg="white").pack(anchor="w")

key_log = tk.Text(log_frame, width=60, height=8, bg="#222222", fg="lime", state="disabled")
key_log.pack()

tk.Button(log_frame, text="Vider le log", command=lambda: key_log.config(state="normal") or key_log.delete(1.0, "end") or key_log.config(state="disabled")).pack(pady=2)

# === Lancer le wizard seulement si aucun profil n'existe ===
if not list_profiles():  # Aucun fichier .json dans le dossier "profiles"
    wizard = FirstLaunchWizard(root)
    root.wait_window(wizard.window)  # Attend que le wizard se termine
    refresh_profiles()  # Recharge les profils après création
    profile_var.set(list_profiles()[0])  # Active le premier profil créé
    change_profile(list_profiles()[0])  # Charge les données du profil

root.mainloop()
input("\nAppuie sur Entrée pour quitter...")


window_expanded = True
previous_geometry = ""
btn_restore = None
drag_area = None
restore_frame = None
vertical_frame = None
move_bar = None

def toggle_window_mode():
    global window_expanded, previous_geometry, btn_restore, drag_area, restore_frame, vertical_frame, move_bar

    if window_expanded:
        previous_geometry = root.geometry()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry(f"60x360+{root.winfo_screenwidth()-60}+100")

        for widget in root.winfo_children():
            widget.pack_forget()

        drag_area = tk.Frame(root, bg="#333333")
        drag_area.pack(fill="both", expand=True)

        # Barre de déplacement
        move_bar = tk.Frame(drag_area, bg="#333333", height=10, cursor="fleur")
        move_bar.pack(fill="x")

        def start_move(event):
            root._drag_start_x = event.x
            root._drag_start_y = event.y

        def do_move(event):
            x = root.winfo_pointerx() - root._drag_start_x
            y = root.winfo_pointery() - root._drag_start_y
            root.geometry(f"+{x}+{y}")

        move_bar.bind("<Button-1>", start_move)
        move_bar.bind("<B1-Motion>", do_move)

        # Icônes verticales
        vertical_frame = tk.Frame(drag_area, bg="#333333")
        vertical_frame.pack(pady=10)

        overlay_icon_labels.clear()

        for i in range(6):
            icon_path = entries[i]["icon"]
            if not os.path.exists(icon_path):
                icon_path = DEFAULT_ICON
            try:
                base_img = Image.open(icon_path).convert("RGBA").resize((60, 60), Image.LANCZOS)
                if not entries[i]["enabled"].get():
                    cross_img = Image.open(CROSS_IMAGE_PATH).convert("RGBA").resize((60, 60), Image.LANCZOS)
                    base_img = Image.alpha_composite(base_img, cross_img)
                photo = ImageTk.PhotoImage(base_img)
            except Exception as e:
                print(f"[Overlay] Erreur chargement icône {i+1} :", e)
                photo = None

            icon_label = tk.Label(vertical_frame, image=photo, bg="#333333")
            icon_label.image = photo
            icon_label.pack(pady=2)
            overlay_icon_labels.append(icon_label)

            def on_double_click(e, i=i):
                toggle_sort_enabled(i)
                update_overlay_icons_only()

            icon_label.bind("<Double-Button-1>", on_double_click)

        restore_frame = tk.Frame(drag_area, bg="#222222")
        restore_frame.pack(fill="x", side="bottom")

        btn_restore = tk.Button(restore_frame, text=">>", command=toggle_window_mode,
                                bg="#444444", fg="white")
        btn_restore.pack(padx=5, pady=5)

        reduce_button.pack_forget()
        window_expanded = False

    else:
        if btn_restore:
            btn_restore.destroy()
            btn_restore = None
        if restore_frame:
            restore_frame.destroy()
            restore_frame = None
        if vertical_frame:
            vertical_frame.destroy()
            vertical_frame = None
        if drag_area:
            drag_area.destroy()
            drag_area = None
        if move_bar:
            move_bar.destroy()
            move_bar = None

        root.overrideredirect(False)
        root.attributes("-topmost", False)
        root.update_idletasks()
        root.geometry(previous_geometry)

        for widget in root.winfo_children():
            widget.pack()
        reduce_button.pack(side="bottom", anchor="e", padx=10, pady=10)
        window_expanded = True

