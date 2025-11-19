import tkinter as tk
import db
from ui import App


if __name__ == '__main__':
    db.create_db()
    root = tk.Tk()
    app = App(root)
    root.mainloop()
