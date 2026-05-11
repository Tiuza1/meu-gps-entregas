import tkinter as tk
import pyautogui
from threading import Thread
import time

class MiraVisual:
    def __init__(self, root):
        self.root = root
        self.root.title("Localizador")
        self.root.geometry("250x120")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        
        self.lbl_pos = tk.Label(root, text="X: -- Y: --", fg="white", bg="#1e1e1e", font=("Arial", 12))
        self.lbl_pos.pack(pady=10)
        
        self.lbl_cor = tk.Label(root, text="RGB: --", fg="cyan", bg="#1e1e1e", font=("Arial", 10))
        self.lbl_cor.pack()

        self.lbl_dif = tk.Label(root, text="Dif (B-R): --", fg="yellow", bg="#1e1e1e", font=("Arial", 10))
        self.lbl_dif.pack()

        Thread(target=self.atualizar, daemon=True).start()

    def atualizar(self):
        while True:
            x, y = pyautogui.position()
            try:
                rgb = pyautogui.pixel(x, y)
                dif = rgb[2] - rgb[0] # Azul - Vermelho
                self.lbl_pos.config(text=f"X: {x}  Y: {y}")
                self.lbl_cor.config(text=f"RGB: {rgb}")
                self.lbl_dif.config(text=f"Diferença (B-R): {dif}")
            except:
                pass
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = MiraVisual(root)
    root.mainloop()