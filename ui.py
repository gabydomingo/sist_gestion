import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from datetime import timedelta
import uuid 
import os
import pandas as pd
from tkcalendar import DateEntry 

from db import (
    create_db,
    get_categorias,
    add_categoria,
    update_categoria,
    delete_categoria,
    get_sanguches,
    get_sanguches_simple,
    add_sanguche,
    update_sanguche,
    delete_sanguche,
    add_venta,
    abrir_caja,
    cerrar_caja,
    get_ultima_sesion_abierta,
    get_ventas_detalladas_por_sesion,
    get_totales_ventas_por_sesion,
    add_gasto,
    get_gastos_detallados_por_sesion,
    get_resumen_gastos_por_sesion,
    get_total_gastos_por_sesion,
    add_cliente,
    get_clientes,
    buscar_clientes_por_nombre,
    update_cliente,
    delete_cliente,
    # --- NUEVAS IMPORTACIONES PARA REPORTES ---
    get_ventas_detalladas_por_rango,
    get_gastos_detallados_por_rango,
    get_totales_ventas_por_rango,
    get_total_gastos_por_rango
)

# ------------------------------------------------
# CLASE PEDIDO (SIN CAMBIOS)
# ------------------------------------------------
class Pedido:
    def __init__(self, id, cliente_id, cliente_nombre):
        self.id = id
        self.cliente_id = cliente_id
        self.cliente_nombre = cliente_nombre
        self.items = {} 
        self.total = 0.0
        self.timestamp_creacion = datetime.datetime.now()
        self.estado = "activo"
        self.descuento = 0.0
        self.total_final = 0.0

    def recalcular_total(self):
        self.total = sum(item['subtotal'] for item in self.items.values())
        if self.descuento > self.total:
            self.descuento = self.total
        self.total_final = self.total - self.descuento
    def agregar_item(self, sanguche_datos, cantidad):
        subtotal = sanguche_datos[2] * cantidad
        item_id = str(uuid.uuid4()) 
        self.items[item_id] = {"datos": sanguche_datos, "cantidad": cantidad, "subtotal": subtotal}
        self.recalcular_total()
        return item_id
    def quitar_item(self, item_id):
        if item_id in self.items:
            del self.items[item_id]
            self.recalcular_total()
    def aplicar_descuento(self, tipo: str, valor: float):
        if tipo == '%': self.descuento = self.total * (valor / 100)
        elif tipo == '$': self.descuento = valor
        else: self.descuento = 0.0
        self.recalcular_total()
    def get_tiempo_transcurrido(self):
        delta = datetime.datetime.now() - self.timestamp_creacion
        delta_str = str(timedelta(seconds=int(delta.total_seconds())))
        return delta_str
    def get_items_para_db(self):
        lista_db = []
        for item in self.items.values():
            lista_db.append({"sanguche_id": item['datos'][0], "cantidad": item['cantidad'], "subtotal": item['subtotal']})
        return lista_db


class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Sanguchería")
        self.root.geometry("1024x700")

        # --- Paleta de Colores (Sin cambios) ---
        self.COLOR_MENU = "#343A40"
        self.COLOR_MENU_HOVER = "#495057"
        self.COLOR_PANEL = "#F8F9FA"
        self.COLOR_BOTON_OK = "#28A745"
        self.COLOR_BOTON_EDIT = "#007BFF"
        self.COLOR_BOTON_DEL = "#DC3545"
        self.COLOR_TEXTO_BTN = "#FFFFFF"
        self.COLOR_TITULO = "#333333"
        self.COLOR_TEXTO = "#222222"
        self.FONT_TITULO = ("Segoe UI", 18, "bold")
        self.FONT_LABEL = ("Segoe UI", 12)
        self.FONT_BOTON = ("Segoe UI", 11, "bold")
        self.FONT_MENU = ("Segoe UI", 12, "bold")
        
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", font=self.FONT_LABEL, rowheight=30, background=self.COLOR_PANEL, fieldbackground=self.COLOR_PANEL, foreground=self.COLOR_TEXTO)
        style.map("Treeview", background=[('selected', self.COLOR_BOTON_EDIT)])
        style.configure("Treeview.Heading", font=self.FONT_BOTON, background="#E0E0E0", foreground=self.COLOR_TITULO, relief="flat")
        style.map("Treeview.Heading", background=[('active', "#D0D0D0")])
        style.configure("TCombobox", font=self.FONT_LABEL, fieldbackground=self.COLOR_PANEL)
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[10, 5])
        
        self.root.configure(bg=self.COLOR_PANEL)

        self.pedidos_activos = []
        self.pedido_actual = None
        self.pedido_id_counter = 1
        self.timer_pedidos_activo = False
        
        self.caja_abierta = False
        self.sesion_id = None
        self.sesion_fecha_apertura = None
        self.sesion_monto_inicial = 0.0
        self.botones_menu = {} 
        
        self.menu = tk.Frame(self.root, width=220, bg=self.COLOR_MENU)
        self.menu.pack(side="left", fill="y")
        self.panel = tk.Frame(self.root, bg=self.COLOR_PANEL)
        self.panel.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.crear_menu()
        self.verificar_caja_abierta()
        
        if not self.caja_abierta:
            self.pantalla_caja()
        else:
            self.pantalla_inicio() # <-- Ahora la pantalla de inicio es el Dashboard

    # ------------------------------------------------
    # MENÚ PRINCIPAL Y UTILIDADES
    # ------------------------------------------------
    def crear_menu(self):
        tk.Label(self.menu, text="Sanguchería", fg="white", bg=self.COLOR_MENU,
                 font=("Segoe UI", 20, "bold")).pack(pady=30, padx=20)
        
        # --- MODIFICADO: Añadido "Reportes" ---
        opciones = [
            ("Dashboard", self.pantalla_inicio), # <-- 'pantalla_inicio' es el nuevo Dashboard
            ("Categorías", self.pantalla_categorias),
            ("Sanguches", self.pantalla_sanguches),
            ("Clientes", self.pantalla_clientes),
            ("Pedidos", self.pantalla_lista_pedidos),
            ("Gastos", self.pantalla_gastos),
            ("Reportes", self.pantalla_reportes), # <-- NUEVO
            ("Caja", self.pantalla_caja)
        ]
        
        for texto, comando in opciones:
            btn = tk.Button(self.menu, text=texto, command=comando,
                            font=self.FONT_MENU, bg=self.COLOR_MENU, fg="white",
                            relief="flat", anchor="w", padx=20, pady=10)
            btn.pack(fill="x", pady=2)
            btn.bind("<Enter>", self.on_menu_enter)
            btn.bind("<Leave>", self.on_menu_leave)
            if texto not in ["Caja", "Reportes"]: # Reportes se puede ver con caja cerrada
                self.botones_menu[texto] = btn

    def actualizar_estado_menu(self):
        estado = "normal" if self.caja_abierta else "disabled"
        for nombre, boton in self.botones_menu.items():
            boton.config(state=estado)
            if estado == "disabled":
                boton.config(bg=self.COLOR_MENU_HOVER)
            else:
                boton.config(bg=self.COLOR_MENU)

    def verificar_caja_abierta(self):
        sesion_abierta = get_ultima_sesion_abierta()
        if sesion_abierta:
            self.sesion_id, self.sesion_fecha_apertura, self.sesion_monto_inicial = sesion_abierta
            self.caja_abierta = True
            self.pedido_id_counter = (self.sesion_id * 1000) + 1
        else:
            self.caja_abierta = False
        self.actualizar_estado_menu()

    def on_menu_enter(self, e):
        if e.widget['state'] == "normal":
            e.widget.config(bg=self.COLOR_MENU_HOVER)

    def on_menu_leave(self, e):
        if e.widget['state'] == "normal":
            e.widget.config(bg=self.COLOR_MENU)

    def limpiar_panel(self):
        self.timer_pedidos_activo = False
        for w in self.panel.winfo_children():
            w.destroy()
            
    def crear_boton_estilizado(self, master, texto, color_bg, comando, width=20):
        btn = tk.Button(master, text=texto, command=comando,
                        font=self.FONT_BOTON, bg=color_bg, fg=self.COLOR_TEXTO_BTN,
                        relief="flat", pady=8, padx=12, width=width)
        return btn

    # ------------------------------------------------
    # CATEGORÍAS (SIN CAMBIOS)
    # ------------------------------------------------
    def pantalla_categorias(self):
        self.limpiar_panel()
        tk.Label(self.panel, text="Gestión de Categorías", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        self.lista_categorias = tk.Listbox(self.panel, font=self.FONT_LABEL, height=10, borderwidth=0, highlightthickness=1, relief="solid", highlightcolor="#DDDDDD")
        self.lista_categorias.pack(fill="x", expand=False, padx=20, pady=10)
        self.lista_categorias.bind("<Double-Button-1>", self.editar_categoria_popup)
        self.cargar_categorias()
        form_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL)
        form_frame.pack(pady=20, fill="x", padx=20)
        tk.Label(form_frame, text="Nueva categoría:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(side="left", padx=(0, 10))
        self.entry_categoria = tk.Entry(form_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=30)
        self.entry_categoria.pack(side="left", padx=10, ipady=5)
        btn_agregar = self.crear_boton_estilizado(form_frame, "Agregar", self.COLOR_BOTON_OK, self.agregar_categoria, width=10)
        btn_agregar.pack(side="left", padx=10)
        btn_borrar_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL)
        btn_borrar_frame.pack(pady=10, padx=20, anchor="e")
        btn_borrar = self.crear_boton_estilizado(btn_borrar_frame, "Borrar Seleccionada", self.COLOR_BOTON_DEL, self.borrar_categoria)
        btn_borrar.pack()

    def cargar_categorias(self):
        self.lista_categorias.delete(0, tk.END)
        for cat in get_categorias():
            self.lista_categorias.insert(tk.END, f" {cat[1]}")
            self.lista_categorias.itemconfig(tk.END, {'fg': self.COLOR_TEXTO})
    def agregar_categoria(self):
        nombre = self.entry_categoria.get().strip()
        if not nombre: return
        add_categoria(nombre); self.cargar_categorias(); self.entry_categoria.delete(0, tk.END)
    def editar_categoria_popup(self, event):
        try:
            seleccion_idx = self.lista_categorias.curselection()
            if not seleccion_idx: return
            seleccion_texto = self.lista_categorias.get(seleccion_idx).strip()
            cat_id = [c[0] for c in get_categorias() if c[1] == seleccion_texto][0]
        except Exception as e:
            print(e); return
        popup = tk.Toplevel(self.root, bg=self.COLOR_PANEL); popup.title("Editar Categoría"); popup.geometry("350x150")
        tk.Label(popup, text="Nuevo nombre:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10)
        entry_edit = tk.Entry(popup, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=30)
        entry_edit.insert(0, seleccion_texto); entry_edit.pack(pady=5, padx=20, ipady=5)
        def guardar():
            nuevo = entry_edit.get().strip()
            if nuevo: update_categoria(cat_id, nuevo); popup.destroy(); self.cargar_categorias()
        btn_guardar = self.crear_boton_estilizado(popup, "Guardar", self.COLOR_BOTON_OK, guardar); btn_guardar.pack(pady=10)
    def borrar_categoria(self):
        try:
            seleccion_idx = self.lista_categorias.curselection()
            if not seleccion_idx: return
            seleccion_texto = self.lista_categorias.get(seleccion_idx).strip()
            cat_id = [c[0] for c in get_categorias() if c[1] == seleccion_texto][0]
        except: return
        if messagebox.askyesno("Confirmar", f"¿Seguro que desea borrar la categoría '{seleccion_texto}'?"):
            delete_categoria(cat_id); self.cargar_categorias()

    # ------------------------------------------------
    # SANGUCHES (SIN CAMBIOS)
    # ------------------------------------------------
    def pantalla_sanguches(self):
        self.limpiar_panel()
        tk.Label(self.panel, text="Gestión de Sanguches", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        tree_frame = tk.Frame(self.panel); tree_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.tree_sanguches = ttk.Treeview(tree_frame, columns=("nombre", "cat", "precio"), show="headings", style="Treeview")
        self.tree_sanguches.heading("nombre", text="Nombre"); self.tree_sanguches.heading("cat", text="Categoría"); self.tree_sanguches.heading("precio", text="Precio")
        self.tree_sanguches.column("nombre", width=300); self.tree_sanguches.column("cat", width=150); self.tree_sanguches.column("precio", width=100, anchor="e")
        self.tree_sanguches.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_sanguches.yview)
        self.tree_sanguches.configure(yscroll=scrollbar.set); scrollbar.pack(side="right", fill="y")
        self.tree_sanguches.bind("<Double-Button-1>", self.ver_ingredientes)
        self.cargar_sanguches()
        btn_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); btn_frame.pack(pady=20, fill="x", padx=20)
        btn_agregar = self.crear_boton_estilizado(btn_frame, "Agregar Sanguche", self.COLOR_BOTON_OK, self.popup_agregar_sanguche); btn_agregar.pack(side="left", padx=10)
        btn_editar = self.crear_boton_estilizado(btn_frame, "Editar Sanguche", self.COLOR_BOTON_EDIT, self.popup_editar_sanguche); btn_editar.pack(side="left", padx=10)
        btn_borrar = self.crear_boton_estilizado(btn_frame, "Borrar Sanguche", self.COLOR_BOTON_DEL, self.borrar_sanguche); btn_borrar.pack(side="right", padx=10)
    def cargar_sanguches(self):
        for item in self.tree_sanguches.get_children(): self.tree_sanguches.delete(item)
        for s in get_sanguches():
            precio_formateado = f"${s[3]:.2f}"; categoria_nombre = s[4] if s[4] else "Sin Categoría"
            self.tree_sanguches.insert("", "end", iid=s[0], values=(s[1], categoria_nombre, precio_formateado))
    def ver_ingredientes(self, event):
        try: ID = int(self.tree_sanguches.selection()[0])
        except: return
        datos = [s for s in get_sanguches() if s[0] == ID][0]
        popup = tk.Toplevel(self.root, bg=self.COLOR_PANEL); popup.title(datos[1]); popup.geometry("400x200")
        tk.Label(popup, text="Ingredientes:", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=10)
        tk.Label(popup, text=datos[2], font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO, wraplength=380).pack(pady=10, padx=20)
    def _crear_popup_formulario_sanguche(self, titulo, sanguche_datos=None):
        popup = tk.Toplevel(self.root, bg=self.COLOR_PANEL); popup.title(titulo); popup.geometry("450x450")
        frame = tk.Frame(popup, bg=self.COLOR_PANEL); frame.pack(pady=20, padx=30, fill="both", expand=True)
        tk.Label(frame, text="Nombre", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_nombre = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_nombre.pack(pady=(0, 10), ipady=5, fill="x")
        tk.Label(frame, text="Ingredientes", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_ing = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_ing.pack(pady=(0, 10), ipady=5, fill="x")
        tk.Label(frame, text="Precio", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_precio = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_precio.pack(pady=(0, 10), ipady=5, fill="x")
        tk.Label(frame, text="Categoría", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        categorias = get_categorias(); self.cat_map = {nombre: id for id, nombre in categorias}
        combo_cat = ttk.Combobox(frame, values=[c[1] for c in categorias], state="readonly", font=self.FONT_LABEL, width=38)
        combo_cat.pack(pady=(0, 20), ipady=5, fill="x")
        if sanguche_datos:
            entry_nombre.insert(0, sanguche_datos[1]); entry_ing.insert(0, sanguche_datos[2]); entry_precio.insert(0, sanguche_datos[3])
            combo_cat.set(sanguche_datos[4] if sanguche_datos[4] else "")
        return popup, entry_nombre, entry_ing, entry_precio, combo_cat, self.cat_map
    def popup_agregar_sanguche(self):
        popup, entry_nombre, entry_ing, entry_precio, combo_cat, cat_map = self._crear_popup_formulario_sanguche("Nuevo Sanguche")
        def guardar():
            nombre = entry_nombre.get(); ingredientes = entry_ing.get()
            try: precio = float(entry_precio.get())
            except: messagebox.showerror("Error", "El precio debe ser numérico.", parent=popup); return
            cat_nombre = combo_cat.get()
            if not cat_nombre: messagebox.showerror("Error", "Debe seleccionar una categoría.", parent=popup); return
            cat_id = cat_map.get(cat_nombre)
            add_sanguche(nombre, ingredientes, precio, cat_id); popup.destroy(); self.cargar_sanguches()
        btn_guardar = self.crear_boton_estilizado(popup, "Guardar", self.COLOR_BOTON_OK, guardar); btn_guardar.pack(pady=10)
    def popup_editar_sanguche(self):
        try: ID = self.tree_sanguches.selection()[0]
        except: messagebox.showerror("Error", "Seleccione un sanguche para editar."); return
        datos_actuales = [s for s in get_sanguches() if s[0] == int(ID)][0]
        popup, entry_nombre, entry_ing, entry_precio, combo_cat, cat_map = self._crear_popup_formulario_sanguche("Editar Sanguche", datos_actuales)
        def guardar():
            nombre = entry_nombre.get(); ingredientes = entry_ing.get()
            try: precio = float(entry_precio.get())
            except: messagebox.showerror("Error", "El precio debe ser numérico.", parent=popup); return
            cat_nombre = combo_cat.get(); cat_id = cat_map.get(cat_nombre) if cat_nombre else None
            update_sanguche(ID, nombre, ingredientes, precio, cat_id); popup.destroy(); self.cargar_sanguches()
        btn_guardar = self.crear_boton_estilizado(popup, "Guardar Cambios", self.COLOR_BOTON_OK, guardar); btn_guardar.pack(pady=10)
    def borrar_sanguche(self):
        try: ID = self.tree_sanguches.selection()[0]; nombre_sanguche = self.tree_sanguches.item(ID)['values'][0]
        except: messagebox.showerror("Error", "Seleccione un sanguche para borrar."); return
        if messagebox.askyesno("Confirmar", f"¿Seguro que desea borrar '{nombre_sanguche}'?"):
            delete_sanguche(ID); self.cargar_sanguches()

    # ------------------------------------------------
    # PANTALLA DE CLIENTES (SIN CAMBIOS)
    # ------------------------------------------------
    def pantalla_clientes(self):
        self.limpiar_panel()
        tk.Label(self.panel, text="Gestión de Clientes", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        tree_frame = tk.Frame(self.panel); tree_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.tree_clientes = ttk.Treeview(tree_frame, columns=("id", "nombre", "telefono", "email"), show="headings", style="Treeview")
        self.tree_clientes.heading("id", text="ID"); self.tree_clientes.heading("nombre", text="Nombre"); self.tree_clientes.heading("telefono", text="Teléfono"); self.tree_clientes.heading("email", text="Email")
        self.tree_clientes.column("id", width=50, anchor="center"); self.tree_clientes.column("nombre", width=250); self.tree_clientes.column("telefono", width=150); self.tree_clientes.column("email", width=250)
        self.tree_clientes.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_clientes.yview)
        self.tree_clientes.configure(yscroll=scrollbar.set); scrollbar.pack(side="right", fill="y")
        self.cargar_clientes()
        btn_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); btn_frame.pack(pady=20, fill="x", padx=20)
        btn_agregar = self.crear_boton_estilizado(btn_frame, "Agregar Cliente", self.COLOR_BOTON_OK, self.popup_agregar_cliente); btn_agregar.pack(side="left", padx=10)
        btn_editar = self.crear_boton_estilizado(btn_frame, "Editar Cliente", self.COLOR_BOTON_EDIT, self.popup_editar_cliente); btn_editar.pack(side="left", padx=10)
    def cargar_clientes(self):
        for item in self.tree_clientes.get_children(): self.tree_clientes.delete(item)
        for c in get_clientes():
            self.tree_clientes.insert("", "end", iid=c[0], values=(c[0], c[1], c[2] or "", c[3] or ""))
    def _crear_popup_formulario_cliente(self, titulo, cliente_datos=None):
        popup = tk.Toplevel(self.root, bg=self.COLOR_PANEL); popup.title(titulo); popup.geometry("400x300")
        frame = tk.Frame(popup, bg=self.COLOR_PANEL); frame.pack(pady=20, padx=30, fill="both", expand=True)
        tk.Label(frame, text="Nombre (*)", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_nombre = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_nombre.pack(pady=(0, 10), ipady=5, fill="x")
        tk.Label(frame, text="Teléfono", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_tel = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_tel.pack(pady=(0, 10), ipady=5, fill="x")
        tk.Label(frame, text="Email", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        entry_email = tk.Entry(frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=40); entry_email.pack(pady=(0, 10), ipady=5, fill="x")
        if cliente_datos:
            entry_nombre.insert(0, cliente_datos[1]); entry_tel.insert(0, cliente_datos[2] or ""); entry_email.insert(0, cliente_datos[3] or "")
        return popup, entry_nombre, entry_tel, entry_email
    def popup_agregar_cliente(self):
        popup, entry_nombre, entry_tel, entry_email = self._crear_popup_formulario_cliente("Nuevo Cliente")
        def guardar():
            nombre = entry_nombre.get().strip(); tel = entry_tel.get().strip() or None; email = entry_email.get().strip() or None
            if not nombre: messagebox.showerror("Error", "El campo 'Nombre' es obligatorio.", parent=popup); return
            add_cliente(nombre, tel, email); popup.destroy(); self.cargar_clientes()
        btn_guardar = self.crear_boton_estilizado(popup, "Guardar", self.COLOR_BOTON_OK, guardar); btn_guardar.pack(pady=10)
    def popup_editar_cliente(self):
        try:
            ID = self.tree_clientes.selection()[0]; datos_actuales = self.tree_clientes.item(ID)['values']
        except: messagebox.showerror("Error", "Seleccione un cliente para editar."); return
        datos_formato = (datos_actuales[0], datos_actuales[1], datos_actuales[2], datos_actuales[3])
        popup, entry_nombre, entry_tel, entry_email = self._crear_popup_formulario_cliente("Editar Cliente", datos_formato)
        def guardar():
            nombre = entry_nombre.get().strip(); tel = entry_tel.get().strip() or None; email = entry_email.get().strip() or None
            if not nombre: messagebox.showerror("Error", "El campo 'Nombre' es obligatorio.", parent=popup); return
            update_cliente(ID, nombre, tel, email); popup.destroy(); self.cargar_clientes()
        btn_guardar = self.crear_boton_estilizado(popup, "Guardar Cambios", self.COLOR_BOTON_OK, guardar); btn_guardar.pack(pady=10)

    # ------------------------------------------------
    # GESTIÓN DE PEDIDOS (SIN CAMBIOS)
    # ------------------------------------------------
    def pantalla_lista_pedidos(self):
        self.limpiar_panel(); self.pedido_actual = None
        tk.Label(self.panel, text="Pedidos Activos", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        tree_frame = tk.Frame(self.panel); tree_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.tree_pedidos_activos = ttk.Treeview(tree_frame, columns=("id", "cliente", "total", "tiempo"), show="headings", style="Treeview")
        self.tree_pedidos_activos.heading("id", text="ID"); self.tree_pedidos_activos.heading("cliente", text="Cliente"); self.tree_pedidos_activos.heading("total", text="Total"); self.tree_pedidos_activos.heading("tiempo", text="Tiempo")
        self.tree_pedidos_activos.column("id", width=50, anchor="center"); self.tree_pedidos_activos.column("cliente", width=250); self.tree_pedidos_activos.column("total", width=100, anchor="e"); self.tree_pedidos_activos.column("tiempo", width=100, anchor="center")
        self.tree_pedidos_activos.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_pedidos_activos.yview)
        self.tree_pedidos_activos.configure(yscroll=scrollbar.set); scrollbar.pack(side="right", fill="y")
        btn_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); btn_frame.pack(pady=20, fill="x", padx=20)
        btn_nuevo = self.crear_boton_estilizado(btn_frame, "Nuevo Pedido", self.COLOR_BOTON_OK, self.popup_buscar_cliente_para_pedido); btn_nuevo.pack(side="left", padx=10)
        btn_editar = self.crear_boton_estilizado(btn_frame, "Ver / Editar", self.COLOR_BOTON_EDIT, self.editar_pedido_seleccionado); btn_editar.pack(side="left", padx=10)
        btn_cobrar = self.crear_boton_estilizado(btn_frame, "Cobrar Pedido", self.COLOR_BOTON_OK, self.cobrar_pedido_seleccionado); btn_cobrar.pack(side="right", padx=10)
        btn_cancelar = self.crear_boton_estilizado(btn_frame, "Cancelar Pedido", self.COLOR_BOTON_DEL, self.cancelar_pedido_seleccionado); btn_cancelar.pack(side="right", padx=10)
        self.cargar_lista_pedidos(); self.iniciar_timer_pedidos()
    def cargar_lista_pedidos(self):
        if not hasattr(self, 'tree_pedidos_activos'): return
        for item in self.tree_pedidos_activos.get_children(): self.tree_pedidos_activos.delete(item)
        for pedido in self.pedidos_activos:
            self.tree_pedidos_activos.insert("", "end", iid=pedido.id,
                values=(f"#{pedido.id}", pedido.cliente_nombre, f"${pedido.total_final:.2f}", pedido.get_tiempo_transcurrido()))
    def iniciar_timer_pedidos(self):
        self.timer_pedidos_activo = True; self.actualizar_timers_pedidos()
    def actualizar_timers_pedidos(self):
        if not self.timer_pedidos_activo: return
        try:
            for pedido in self.pedidos_activos:
                if self.tree_pedidos_activos.exists(pedido.id):
                    self.tree_pedidos_activos.set(pedido.id, column="tiempo", value=pedido.get_tiempo_transcurrido())
                    self.tree_pedidos_activos.set(pedido.id, column="total", value=f"${pedido.total_final:.2f}")
            self.root.after(1000, self.actualizar_timers_pedidos)
        except Exception as e:
            print(f"Error en timer: {e}"); self.timer_pedidos_activo = False
    def popup_buscar_cliente_para_pedido(self):
        popup = tk.Toplevel(self.root, bg=self.COLOR_PANEL); popup.title("Nuevo Pedido - Seleccionar Cliente"); popup.geometry("500x400")
        search_frame = tk.Frame(popup, bg=self.COLOR_PANEL); search_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(search_frame, text="Buscar Cliente:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(side="left", padx=(0,10))
        entry_buscar = tk.Entry(search_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=30)
        entry_buscar.pack(side="left", ipady=5)
        list_frame = tk.Frame(popup, bg=self.COLOR_PANEL); list_frame.pack(fill="both", expand=True, padx=20, pady=5)
        listbox_clientes = tk.Listbox(list_frame, font=self.FONT_LABEL, borderwidth=1, relief="solid")
        listbox_clientes.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox_clientes.yview)
        listbox_clientes.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        def buscar_cliente(event=None):
            listbox_clientes.delete(0, tk.END)
            termino = entry_buscar.get().strip()
            clientes_encontrados = buscar_clientes_por_nombre(termino)
            listbox_clientes.client_data = {} 
            for (id, nombre, tel, email) in clientes_encontrados:
                texto = f"{nombre} - (Tel: {tel or 'N/A'})"
                listbox_clientes.insert(tk.END, texto)
                listbox_clientes.client_data[texto] = (id, nombre)
        def crear_pedido_con_cliente():
            try:
                seleccion_texto = listbox_clientes.get(listbox_clientes.curselection())
                cliente_id, cliente_nombre = listbox_clientes.client_data[seleccion_texto]
            except:
                messagebox.showerror("Error", "Debe seleccionar un cliente de la lista.", parent=popup); return
            self._crear_pedido_objeto(cliente_id, cliente_nombre)
            popup.destroy(); self.pantalla_editar_pedido()
        def crear_pedido_consumidor_final():
            self._crear_pedido_objeto(None, "Consumidor Final")
            popup.destroy(); self.pantalla_editar_pedido()
        entry_buscar.bind("<KeyRelease>", buscar_cliente); buscar_cliente()
        btn_frame = tk.Frame(popup, bg=self.COLOR_PANEL); btn_frame.pack(fill="x", padx=20, pady=10)
        btn_crear = self.crear_boton_estilizado(btn_frame, "Usar Cliente Seleccionado", self.COLOR_BOTON_OK, crear_pedido_con_cliente, width=22)
        btn_crear.pack(side="left", expand=True)
        btn_final = self.crear_boton_estilizado(btn_frame, "Consumidor Final", self.COLOR_BOTON_EDIT, crear_pedido_consumidor_final, width=22)
        btn_final.pack(side="right", expand=True)
    def _crear_pedido_objeto(self, cliente_id, cliente_nombre):
        nuevo_id = self.pedido_id_counter; self.pedido_id_counter += 1
        nuevo_pedido = Pedido(id=nuevo_id, cliente_id=cliente_id, cliente_nombre=cliente_nombre)
        self.pedidos_activos.append(nuevo_pedido); self.pedido_actual = nuevo_pedido
    def _get_pedido_seleccionado(self):
        try:
            seleccion_id = self.tree_pedidos_activos.selection()[0]; pedido_id = int(seleccion_id)
            pedido_obj = next((p for p in self.pedidos_activos if p.id == pedido_id), None); return pedido_obj
        except:
            messagebox.showerror("Error", "Seleccione un pedido de la lista."); return None
    def editar_pedido_seleccionado(self):
        pedido = self._get_pedido_seleccionado()
        if pedido: self.pedido_actual = pedido; self.pantalla_editar_pedido()
    def cobrar_pedido_seleccionado(self):
        pedido = self._get_pedido_seleccionado()
        if pedido:
            if not pedido.items: messagebox.showerror("Error", "Este pedido no tiene items."); return
            self.pedido_actual = pedido; self.pantalla_pago()
    def cancelar_pedido_seleccionado(self):
        pedido = self._get_pedido_seleccionado()
        if pedido:
            if messagebox.askyesno("Confirmar", f"¿Seguro que desea cancelar el pedido #{pedido.id} de {pedido.cliente_nombre}?"):
                self.pedidos_activos.remove(pedido); self.cargar_lista_pedidos()
    def pantalla_editar_pedido(self):
        self.limpiar_panel()
        if not self.pedido_actual: messagebox.showerror("Error", "No hay ningún pedido seleccionado."); self.pantalla_lista_pedidos(); return
        tk.Label(self.panel, text=f"Editando Pedido #{self.pedido_actual.id} - Cliente: {self.pedido_actual.cliente_nombre}", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        panel_izq = tk.Frame(self.panel, bg=self.COLOR_PANEL); panel_izq.pack(side="left", fill="both", expand=True, padx=(20, 10))
        panel_der = tk.Frame(self.panel, bg=self.COLOR_PANEL); panel_der.pack(side="right", fill="both", expand=True, padx=(10, 20))
        tk.Label(panel_izq, text="Menú (Doble click para agregar)", font=("Segoe UI", 14, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        tree_menu_frame = tk.Frame(panel_izq); tree_menu_frame.pack(fill="both", expand=True, pady=10)
        self.tree_menu_pedidos = ttk.Treeview(tree_menu_frame, columns=("nombre", "precio"), show="headings", style="Treeview")
        self.tree_menu_pedidos.heading("nombre", text="Sanguche"); self.tree_menu_pedidos.heading("precio", text="Precio")
        self.tree_menu_pedidos.column("nombre", width=200); self.tree_menu_pedidos.column("precio", width=80, anchor="e")
        self.tree_menu_pedidos.pack(side="left", fill="both", expand=True)
        scrollbar_menu = ttk.Scrollbar(tree_menu_frame, orient="vertical", command=self.tree_menu_pedidos.yview)
        self.tree_menu_pedidos.configure(yscroll=scrollbar_menu.set); scrollbar_menu.pack(side="right", fill="y")
        self.sanguches_disponibles = get_sanguches_simple()
        for s in self.sanguches_disponibles: self.tree_menu_pedidos.insert("", "end", iid=s[0], values=(s[1], f"${s[2]:.2f}"))
        self.tree_menu_pedidos.bind("<Double-Button-1>", self.agregar_item_al_pedido)
        controles_frame = tk.Frame(panel_izq, bg=self.COLOR_PANEL); controles_frame.pack(fill="x", pady=10)
        tk.Label(controles_frame, text="Cantidad:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(side="left", padx=10)
        self.entry_cant_pedido = tk.Entry(controles_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=5)
        self.entry_cant_pedido.insert(0, "1"); self.entry_cant_pedido.pack(side="left", ipady=5)
        btn_agregar_manual = self.crear_boton_estilizado(controles_frame, "Agregar item", self.COLOR_BOTON_EDIT, self.agregar_item_al_pedido, width=15)
        btn_agregar_manual.pack(side="left", padx=20)
        tk.Label(panel_der, text="Items en este Pedido", font=("Segoe UI", 14, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        tree_items_frame = tk.Frame(panel_der); tree_items_frame.pack(fill="both", expand=True, pady=10)
        self.tree_items_pedido = ttk.Treeview(tree_items_frame, columns=("cant", "nombre", "subtotal"), show="headings", style="Treeview")
        self.tree_items_pedido.heading("cant", text="Cant."); self.tree_items_pedido.heading("nombre", text="Producto"); self.tree_items_pedido.heading("subtotal", text="Subtotal")
        self.tree_items_pedido.column("cant", width=40, anchor="center"); self.tree_items_pedido.column("nombre", width=180); self.tree_items_pedido.column("subtotal", width=80, anchor="e")
        self.tree_items_pedido.pack(side="left", fill="both", expand=True)
        scrollbar_items = ttk.Scrollbar(tree_items_frame, orient="vertical", command=self.tree_items_pedido.yview)
        self.tree_items_pedido.configure(yscroll=scrollbar_items.set); scrollbar_items.pack(side="right", fill="y")
        self.label_total_pedido = tk.Label(panel_der, text=f"Total: ${self.pedido_actual.total_final:.2f}", font=("Segoe UI", 16, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_OK)
        self.label_total_pedido.pack(pady=10, anchor="e")
        self.cargar_items_del_pedido()
        btn_frame_abajo = tk.Frame(self.panel, bg=self.COLOR_PANEL); btn_frame_abajo.pack(side="bottom", fill="x", pady=20)
        btn_quitar = self.crear_boton_estilizado(btn_frame_abajo, "Quitar Item", self.COLOR_BOTON_DEL, self.quitar_item_del_pedido); btn_quitar.pack(side="right", padx=(10, 20))
        btn_listo = self.crear_boton_estilizado(btn_frame_abajo, "Guardar y Volver", self.COLOR_BOTON_OK, self.pantalla_lista_pedidos); btn_listo.pack(side="left", padx=20)
        btn_pago = self.crear_boton_estilizado(btn_frame_abajo, "Ir a Pago", self.COLOR_BOTON_OK, self.cobrar_pedido_seleccionado_desde_editar); btn_pago.pack(side="left", padx=10)
    def cargar_items_del_pedido(self):
        if not hasattr(self, 'tree_items_pedido'): return
        for item in self.tree_items_pedido.get_children(): self.tree_items_pedido.delete(item)
        for item_id, item_data in self.pedido_actual.items.items():
            self.tree_items_pedido.insert("", "end", iid=item_id,
                values=(item_data['cantidad'], item_data['datos'][1], f"${item_data['subtotal']:.2f}"))
        self.label_total_pedido.config(text=f"Total: ${self.pedido_actual.total_final:.2f}")
    def agregar_item_al_pedido(self, event=None):
        try: ID = int(self.tree_menu_pedidos.selection()[0])
        except: messagebox.showerror("Error", "Seleccione un sanguche del menú de la izquierda."); return
        try:
            cantidad = int(self.entry_cant_pedido.get())
            if cantidad < 1: raise Exception()
        except: messagebox.showerror("Error", "Cantidad inválida."); return
        datos = [s for s in self.sanguches_disponibles if s[0] == ID][0]
        self.pedido_actual.agregar_item(datos, cantidad)
        self.cargar_items_del_pedido()
        self.entry_cant_pedido.delete(0, tk.END); self.entry_cant_pedido.insert(0, "1")
    def quitar_item_del_pedido(self):
        try: item_id = self.tree_items_pedido.selection()[0]
        except: messagebox.showerror("Error", "Seleccione un item del pedido (panel derecho)."); return
        self.pedido_actual.quitar_item(item_id)
        self.cargar_items_del_pedido()
    def cobrar_pedido_seleccionado_desde_editar(self):
        if not self.pedido_actual.items: messagebox.showerror("Error", "Este pedido no tiene items."); return
        self.pantalla_pago()

    # ------------------------------------------------
    # PAGO (MODIFICADO)
    # ------------------------------------------------
    def pantalla_pago(self):
        if not self.pedido_actual:
            messagebox.showerror("Error", "Error interno: No hay pedido actual.")
            self.pantalla_lista_pedidos()
            return

        self.limpiar_panel()
        tk.Label(self.panel, text=f"Pago — Pedido #{self.pedido_actual.id} ({self.pedido_actual.cliente_nombre})",
                 font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        resumen_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); resumen_frame.pack(fill="x", pady=5, padx=20)
        for item_data in self.pedido_actual.items.values():
            texto = f"{item_data['cantidad']}x {item_data['datos'][1]} - ${item_data['subtotal']:.2f}"
            tk.Label(resumen_frame, text=texto, font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w")
        tk.Label(self.panel, text=f"Subtotal: ${self.pedido_actual.total:.2f}",
                 font=("Segoe UI", 14), bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=(5,0))
        self.label_descuento_aplicado = tk.Label(self.panel, text=f"Descuento: ${self.pedido_actual.descuento:.2f}",
                 font=("Segoe UI", 14), bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_DEL)
        self.label_descuento_aplicado.pack()
        self.label_total_final_pago = tk.Label(self.panel, text=f"Total a pagar: ${self.pedido_actual.total_final:.2f}",
                 font=("Segoe UI", 22, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_OK)
        self.label_total_final_pago.pack(pady=5)
        desc_frame = tk.Frame(self.panel, bg="#E0E0E0", relief="solid", borderwidth=1); desc_frame.pack(pady=5, padx=20, fill="x")
        fila1_desc = tk.Frame(desc_frame, bg="#E0E0E0"); fila1_desc.pack(fill="x", pady=5, padx=10)
        tk.Label(fila1_desc, text="Aplicar Descuento:", font=self.FONT_BOTON, bg="#E0E0E0", fg=self.COLOR_TEXTO).pack(side="left", padx=(0, 10))
        self.tipo_descuento = tk.StringVar(value="%")
        tk.Radiobutton(fila1_desc, text="%", variable=self.tipo_descuento, value="%", font=self.FONT_LABEL, bg="#E0E0E0").pack(side="left")
        tk.Radiobutton(fila1_desc, text="$", variable=self.tipo_descuento, value="$", font=self.FONT_LABEL, bg="#E0E0E0").pack(side="left")
        self.entry_descuento_valor = tk.Entry(fila1_desc, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=8)
        self.entry_descuento_valor.pack(side="left", ipady=5, padx=10)
        btn_aplicar_desc = self.crear_boton_estilizado(fila1_desc, "Aplicar", self.COLOR_BOTON_EDIT, self.aplicar_descuento, width=8)
        btn_aplicar_desc.pack(side="left", padx=10)
        fila2_desc = tk.Frame(desc_frame, bg="#E0E0E0"); fila2_desc.pack(fill="x", pady=5, padx=10)
        tk.Label(fila2_desc, text="Motivo:", font=self.FONT_LABEL, bg="#E0E0E0", fg=self.COLOR_TEXTO).pack(side="left", padx=(0, 10))
        self.entry_descuento_motivo = tk.Entry(fila2_desc, font=self.FONT_LABEL, relief="solid", borderwidth=1)
        self.entry_descuento_motivo.pack(side="left", ipady=5, fill="x", expand=True)
        pago_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); pago_frame.pack(pady=5)
        tk.Label(pago_frame, text="Método de pago:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(side="left", padx=10)
        self.metodo_pago = tk.StringVar()
        opciones = ["Efectivo", "Débito", "Crédito", "Transferencia"]
        combo = ttk.Combobox(pago_frame, textvariable=self.metodo_pago,
                             values=opciones, state="readonly", font=self.FONT_LABEL, width=15)
        combo.pack(side="left", ipady=5)
        self.efectivo_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); self.efectivo_frame.pack(pady=5)
        self.label_monto = tk.Label(self.efectivo_frame, text="Monto entregado:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO)
        self.entry_monto = tk.Entry(self.efectivo_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=10)
        def mostrar(*args): 
            if self.metodo_pago.get() == "Efectivo": self.label_monto.pack(side="left", padx=10); self.entry_monto.pack(side="left", ipady=5)
            else: self.label_monto.pack_forget(); self.entry_monto.pack_forget()
        self.metodo_pago.trace_add("write", mostrar)
        btn_confirmar = self.crear_boton_estilizado(self.panel, "Confirmar Pago", self.COLOR_BOTON_OK, self.confirmar_pago)
        btn_confirmar.pack(pady=10)
        btn_volver = self.crear_boton_estilizado(self.panel, "Volver (no cobrar)", self.COLOR_BOTON_EDIT, self.pantalla_lista_pedidos, width=15)
        btn_volver.pack(pady=5)
    def aplicar_descuento(self):
        if not self.pedido_actual: return
        try:
            valor_str = self.entry_descuento_valor.get()
            if not valor_str: valor = 0.0
            else: valor = float(valor_str)
        except: messagebox.showerror("Error", "El valor del descuento debe ser numérico."); return
        tipo = self.tipo_descuento.get()
        self.pedido_actual.aplicar_descuento(tipo, valor)
        self.label_descuento_aplicado.config(text=f"Descuento: ${self.pedido_actual.descuento:.2f}")
        self.label_total_final_pago.config(text=f"Total a pagar: ${self.pedido_actual.total_final:.2f}")
    def confirmar_pago(self):
        metodo = self.metodo_pago.get()
        if not metodo: messagebox.showerror("Error", "Seleccione método de pago."); return
        vuelto = 0; total_a_pagar = self.pedido_actual.total_final
        if metodo == "Efectivo":
            try: entregado = float(self.entry_monto.get())
            except: messagebox.showerror("Error", "Monto inválido."); return
            if entregado < total_a_pagar: messagebox.showerror("Error", "Falta dinero."); return
            vuelto = entregado - total_a_pagar
        items_para_db = self.pedido_actual.get_items_para_db()
        descuento_aplicado = self.pedido_actual.descuento
        motivo = None
        if descuento_aplicado > 0: motivo = self.entry_descuento_motivo.get().strip()
        add_venta(total_a_pagar, metodo, items_para_db, descuento_aplicado, motivo, self.sesion_id, self.pedido_actual.cliente_id)
        tiempo_total_str = self.pedido_actual.get_tiempo_transcurrido()
        self.mostrar_ticket(vuelto, tiempo_total_str)
    def mostrar_ticket(self, vuelto, tiempo_total):
        cliente = self.pedido_actual.cliente_nombre; total = self.pedido_actual.total_final; descuento = self.pedido_actual.descuento
        self.pedidos_activos.remove(self.pedido_actual); self.pedido_actual = None
        self.limpiar_panel()
        tk.Label(self.panel, text="✅ Venta registrada con éxito", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_OK).pack(pady=20)
        tk.Label(self.panel, text=f"Cliente: {cliente}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=5)
        if descuento > 0:
            tk.Label(self.panel, text=f"Descuento: ${descuento:.2f}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_DEL).pack(pady=5)
        tk.Label(self.panel, text=f"Total Pagado: ${total:.2f}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=5)
        if vuelto > 0:
            tk.Label(self.panel, text=f"Vuelto: ${vuelto:.2f}", font=("Segoe UI", 16, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=10)
        tk.Label(self.panel, text=f"Tiempo de preparación: {tiempo_total}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10)
        btn_volver = self.crear_boton_estilizado(self.panel, "Volver a Pedidos", self.COLOR_BOTON_EDIT, self.pantalla_lista_pedidos)
        btn_volver.pack(pady=20)

    # ------------------------------------------------
    # PANTALLA DE INICIO (NUEVO DASHBOARD)
    # ------------------------------------------------
    def pantalla_inicio(self):
        self.limpiar_panel()
        
        if not self.caja_abierta:
            tk.Label(self.panel, text="Bienvenido al Sistema de Sanguchería",
                     font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=40)
            tk.Label(self.panel, text="La caja está cerrada.",
                     font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10)
            tk.Label(self.panel, text="Seleccione 'Caja' en el menú de la izquierda para abrirla.",
                     font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10)
        else:
            tk.Label(self.panel, text="Dashboard (Sesión Actual)", 
                     font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO
                     ).pack(pady=20, anchor="w")
            
            # Reutilizamos la misma lógica de 'pantalla_caja'
            (total_ventas_netas, total_descuentos) = get_totales_ventas_por_sesion(self.sesion_id)
            total_gastos = get_total_gastos_por_sesion(self.sesion_id)
            balance_neto = total_ventas_netas - total_gastos
            pedidos_pendientes = len(self.pedidos_activos)
            
            resumen_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL)
            resumen_frame.pack(fill="x", pady=10, padx=20)
            
            # Función helper para crear tarjetas de resumen
            def crear_tarjeta(texto_label, valor_label, color_valor):
                card = tk.Frame(resumen_frame, bg="#FFFFFF", relief="solid", borderwidth=1)
                card.pack(side="left", fill="x", expand=True, padx=10, pady=10)
                tk.Label(card, text=texto_label, font=self.FONT_BOTON, bg="#FFFFFF", fg=self.COLOR_TEXTO).pack(pady=(10,0))
                tk.Label(card, text=valor_label, font=("Segoe UI", 24, "bold"), bg="#FFFFFF", fg=color_valor).pack(pady=10)
                
            crear_tarjeta("Ventas Netas", f"${total_ventas_netas:.2f}", self.COLOR_BOTON_OK)
            crear_tarjeta("Gastos", f"(${total_gastos:.2f})", self.COLOR_BOTON_DEL)
            crear_tarjeta("Balance", f"${balance_neto:.2f}", self.COLOR_BOTON_EDIT)
            crear_tarjeta("Pedidos Activos", f"{pedidos_pendientes}", self.COLOR_TITULO)
            
            btn_actualizar = self.crear_boton_estilizado(self.panel, "Actualizar Dashboard", self.COLOR_BOTON_EDIT, self.pantalla_inicio)
            btn_actualizar.pack(pady=20)
            
            tk.Label(self.panel, text="Seleccione una opción del menú para continuar.",
                     font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10)


    # ------------------------------------------------
    # PANTALLA DE GASTOS (SIN CAMBIOS)
    # ------------------------------------------------
    def pantalla_gastos(self):
        self.limpiar_panel()
        tk.Label(self.panel, text="Gestión de Gastos de Hoy", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
        form_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL, relief="solid", borderwidth=1); form_frame.pack(pady=10, padx=20, fill="x")
        tk.Label(form_frame, text="Nuevo Gasto", font=self.FONT_BOTON, bg=self.COLOR_PANEL).grid(row=0, column=0, columnspan=4, pady=10)
        tk.Label(form_frame, text="Producto:", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=1, column=0, padx=10, sticky="w")
        self.gasto_entry_producto = tk.Entry(form_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=30)
        self.gasto_entry_producto.grid(row=1, column=1, pady=5, ipady=5)
        tk.Label(form_frame, text="Cantidad:", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=1, column=2, padx=10, sticky="w")
        self.gasto_entry_cantidad = tk.Entry(form_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=10)
        self.gasto_entry_cantidad.grid(row=1, column=3, pady=5, ipady=5)
        tk.Label(form_frame, text="Total Pagado ($):", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=2, column=0, padx=10, sticky="w")
        self.gasto_entry_total = tk.Entry(form_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=15)
        self.gasto_entry_total.grid(row=2, column=1, pady=5, ipady=5, sticky="w")
        tk.Label(form_frame, text="Método de Pago:", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=2, column=2, padx=10, sticky="w")
        self.gasto_combo_metodo = ttk.Combobox(form_frame, values=["Efectivo", "Débito", "Crédito", "Transferencia"], state="readonly", font=self.FONT_LABEL, width=15)
        self.gasto_combo_metodo.current(0); self.gasto_combo_metodo.grid(row=2, column=3, pady=5, ipady=5)
        btn_agregar_gasto = self.crear_boton_estilizado(form_frame, "Guardar Gasto", self.COLOR_BOTON_OK, self.agregar_gasto)
        btn_agregar_gasto.grid(row=3, column=0, columnspan=4, pady=10)
        tk.Label(self.panel, text="Gastos Registrados en esta Sesión", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=20, anchor="w", padx=20)
        tree_frame = tk.Frame(self.panel); tree_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.tree_gastos = ttk.Treeview(tree_frame, columns=("hora", "producto", "cant", "total", "metodo"), show="headings", style="Treeview")
        self.tree_gastos.heading("hora", text="Hora"); self.tree_gastos.heading("producto", text="Producto"); self.tree_gastos.heading("cant", text="Cantidad")
        self.tree_gastos.heading("total", text="Total"); self.tree_gastos.heading("metodo", text="Pagado con")
        self.tree_gastos.column("hora", width=80); self.tree_gastos.column("producto", width=250); self.tree_gastos.column("cant", width=80)
        self.tree_gastos.column("total", width=100); self.tree_gastos.column("metodo", width=120)
        self.tree_gastos.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_gastos.yview)
        self.tree_gastos.configure(yscroll=scrollbar.set); scrollbar.pack(side="right", fill="y")
        self.cargar_gastos_actuales()
    def cargar_gastos_actuales(self):
        for item in self.tree_gastos.get_children(): self.tree_gastos.delete(item)
        gastos = get_gastos_detallados_por_sesion(self.sesion_id)
        for g in gastos:
            hora = datetime.datetime.strptime(g[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            self.tree_gastos.insert("", "end", values=(hora, g[1], g[2], f"${g[3]:.2f}", g[4]))
    def agregar_gasto(self):
        producto = self.gasto_entry_producto.get().strip(); metodo = self.gasto_combo_metodo.get()
        if not producto or not metodo: messagebox.showerror("Error", "Debe completar 'Producto' y 'Método de Pago'."); return
        try:
            cantidad = float(self.gasto_entry_cantidad.get()); total = float(self.gasto_entry_total.get())
        except: messagebox.showerror("Error", "Cantidad y Total deben ser números."); return
        add_gasto(producto, cantidad, total, metodo, self.sesion_id)
        self.gasto_entry_producto.delete(0, tk.END); self.gasto_entry_cantidad.delete(0, tk.END)
        self.gasto_entry_total.delete(0, tk.END); self.gasto_combo_metodo.current(0)
        self.cargar_gastos_actuales(); messagebox.showinfo("Éxito", "Gasto registrado correctamente.")

    # ------------------------------------------------
    # NUEVA PANTALLA DE REPORTES HISTÓRICOS
    # ------------------------------------------------
    def pantalla_reportes(self):
        self.limpiar_panel()
        
        tk.Label(self.panel, text="Reportes Históricos", 
                 font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO
                 ).pack(pady=20, anchor="w")

        # --- Frame de selección de fechas ---
        fecha_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL, relief="solid", borderwidth=1)
        fecha_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(fecha_frame, text="Fecha Desde:", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=0, column=0, padx=10, pady=10)
        self.reporte_cal_inicio = DateEntry(fecha_frame, font=self.FONT_LABEL, date_pattern='dd/mm/yyyy', width=12)
        self.reporte_cal_inicio.grid(row=0, column=1, padx=5)
        
        tk.Label(fecha_frame, text="Fecha Hasta:", font=self.FONT_LABEL, bg=self.COLOR_PANEL).grid(row=0, column=2, padx=10, pady=10)
        self.reporte_cal_fin = DateEntry(fecha_frame, font=self.FONT_LABEL, date_pattern='dd/mm/yyyy', width=12)
        self.reporte_cal_fin.grid(row=0, column=3, padx=5)
        
        btn_generar = self.crear_boton_estilizado(fecha_frame, "Generar Reporte", self.COLOR_BOTON_OK, self.generar_reporte_historico, width=15)
        btn_generar.grid(row=0, column=4, padx=20, pady=10)

        # --- Frame para mostrar los resultados ---
        self.reporte_frame_resultados = tk.Frame(self.panel, bg=self.COLOR_PANEL)
        self.reporte_frame_resultados.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Este frame se llenará dinámicamente
        tk.Label(self.reporte_frame_resultados, text="Seleccione un rango de fechas y presione 'Generar Reporte'.", 
                 font=self.FONT_LABEL, bg=self.COLOR_PANEL).pack(pady=30)
                 
    def generar_reporte_historico(self):
        """Toma las fechas, busca en la DB y muestra los resultados."""
        
        # 1. Limpiar resultados anteriores
        for w in self.reporte_frame_resultados.winfo_children():
            w.destroy()
        
        # 2. Obtener y formatear fechas
        try:
            # .get_date() devuelve un objeto datetime.date
            fecha_inicio_obj = self.reporte_cal_inicio.get_date()
            fecha_fin_obj = self.reporte_cal_fin.get_date()
            
            # Formato YYYY-MM-DD HH:MM:SS para la query BETWEEN
            fecha_inicio_str = fecha_inicio_obj.strftime('%Y-%m-%d 00:00:00')
            fecha_fin_str = fecha_fin_obj.strftime('%Y-%m-%d 23:59:59')
            
            if fecha_inicio_obj > fecha_fin_obj:
                messagebox.showerror("Error", "La 'Fecha Desde' no puede ser posterior a la 'Fecha Hasta'.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Error de formato de fecha: {e}")
            return

        # 3. Consultar la DB
        ventas_lista = get_ventas_detalladas_por_rango(fecha_inicio_str, fecha_fin_str)
        gastos_lista = get_gastos_detallados_por_rango(fecha_inicio_str, fecha_fin_str)
        (total_neto, total_descuentos) = get_totales_ventas_por_rango(fecha_inicio_str, fecha_fin_str)
        total_gastos = get_total_gastos_por_rango(fecha_inicio_str, fecha_fin_str)
        
        total_bruto = total_neto + total_descuentos
        balance_neto = total_neto - total_gastos

        # 4. Mostrar Totales
        totales_frame = tk.Frame(self.reporte_frame_resultados, bg="#FFFFFF", relief="solid", borderwidth=1)
        totales_frame.pack(fill="x", pady=10)
        
        tk.Label(totales_frame, text=f"Total Ventas Netas: ${total_neto:.2f}", font=("Segoe UI", 14, "bold"), bg="#FFFFFF", fg=self.COLOR_BOTON_OK).pack(pady=5)
        tk.Label(totales_frame, text=f"Total Gastos: ${total_gastos:.2f}", font=("Segoe UI", 14, "bold"), bg="#FFFFFF", fg=self.COLOR_BOTON_DEL).pack(pady=5)
        tk.Label(totales_frame, text=f"Balance Neto: ${balance_neto:.2f}", font=("Segoe UI", 16, "bold"), bg="#FFFFFF", fg=self.COLOR_TITULO).pack(pady=10)

        # 5. Mostrar Detalles en Tabs
        notebook = ttk.Notebook(self.reporte_frame_resultados)
        notebook.pack(fill="both", expand=True, pady=10)
        
        frame_ventas = tk.Frame(notebook, bg=self.COLOR_PANEL)
        frame_gastos = tk.Frame(notebook, bg=self.COLOR_PANEL)
        notebook.add(frame_ventas, text=f'Detalle de Ventas ({len(ventas_lista)})')
        notebook.add(frame_gastos, text=f'Detalle de Gastos ({len(gastos_lista)})')
        
        # Tab de Ventas
        cols_ventas = ("fecha", "cliente", "total", "metodo", "descuento", "motivo")
        tree_ventas = ttk.Treeview(frame_ventas, columns=cols_ventas, show="headings", style="Treeview")
        tree_ventas.heading("fecha", text="Fecha"); tree_ventas.heading("cliente", text="Cliente"); tree_ventas.heading("total", text="Total Neto")
        tree_ventas.heading("metodo", text="Método Pago"); tree_ventas.heading("descuento", text="Descuento"); tree_ventas.heading("motivo", text="Motivo")
        for col in cols_ventas: tree_ventas.column(col, width=120)
        tree_ventas.pack(side="left", fill="both", expand=True)
        scroll_v = ttk.Scrollbar(frame_ventas, orient="vertical", command=tree_ventas.yview)
        tree_ventas.configure(yscroll=scroll_v.set); scroll_v.pack(side="right", fill="y")
        
        for (fecha, total, metodo, descuento, motivo, cliente) in ventas_lista:
            fecha_corta = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            tree_ventas.insert("", "end", values=(fecha_corta, cliente, f"${total:.2f}", metodo, f"${descuento:.2f}", motivo if motivo else ""))

        # Tab de Gastos
        cols_gastos = ("fecha", "producto", "cant", "total", "metodo")
        tree_gastos = ttk.Treeview(frame_gastos, columns=cols_gastos, show="headings", style="Treeview")
        tree_gastos.heading("fecha", text="Fecha"); tree_gastos.heading("producto", text="Producto"); tree_gastos.heading("cant", text="Cantidad")
        tree_gastos.heading("total", text="Total"); tree_gastos.heading("metodo", text="Pagado con")
        for col in cols_gastos: tree_gastos.column(col, width=120)
        tree_gastos.pack(side="left", fill="both", expand=True)
        scroll_g = ttk.Scrollbar(frame_gastos, orient="vertical", command=tree_gastos.yview)
        tree_gastos.configure(yscroll=scroll_g.set); scroll_g.pack(side="right", fill="y")

        for (fecha, producto, cantidad, total, metodo) in gastos_lista:
            fecha_corta = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            tree_gastos.insert("", "end", values=(fecha_corta, producto, cantidad, f"${total:.2f}", metodo))
            
        # 6. Botón de Exportar
        # Usamos lambda para pasar los datos al exportador
        btn_exportar = self.crear_boton_estilizado(self.reporte_frame_resultados, "Exportar a Excel", 
            self.COLOR_BOTON_EDIT, 
            lambda: self.exportar_reporte_historico_excel(
                fecha_inicio_obj, fecha_fin_obj, 
                ventas_lista, gastos_lista, 
                total_neto, total_descuentos, total_gastos
            )
        )
        btn_exportar.pack(pady=10)

    def exportar_reporte_historico_excel(self, fecha_inicio, fecha_fin, ventas_lista, gastos_lista, total_neto, total_descuentos, total_gastos):
        """Crea y guarda un reporte histórico en formato Excel."""
        
        REPORTS_DIR = "reportes"
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        fecha_str = f"{fecha_inicio.strftime('%Y-%m-%d')}_a_{fecha_fin.strftime('%Y-%m-%d')}"
        filename = os.path.join(REPORTS_DIR, f"reporte_historico_{fecha_str}.xlsx")

        # --- Resumen ---
        total_ventas_brutas = total_neto + total_descuentos
        balance_neto = total_neto - total_gastos
        
        resumen_data = {
            "Concepto": ["Fecha Desde", "Fecha Hasta", "Total Ventas Brutas", "Total Descuentos", "Total Ventas Netas", "Total Gastos", "Balance Neto"],
            "Valor": [fecha_inicio.strftime('%d/%m/%Y'), fecha_fin.strftime('%d/%m/%Y'), total_ventas_brutas, total_descuentos, total_neto, total_gastos, balance_neto]
        }
        df_resumen = pd.DataFrame(resumen_data)

        # --- Detalle Ventas ---
        columnas_ventas = ["Fecha Completa", "Total Neto", "Método Pago", "Descuento", "Motivo Descuento", "Cliente"]
        df_ventas = pd.DataFrame(ventas_lista, columns=columnas_ventas)
        df_ventas["Fecha"] = pd.to_datetime(df_ventas["Fecha Completa"]).dt.strftime("%d/%m/%Y %H:%M")
        df_ventas = df_ventas[["Fecha", "Cliente", "Total Neto", "Método Pago", "Descuento", "Motivo Descuento"]]
        df_ventas["Motivo Descuento"] = df_ventas["Motivo Descuento"].fillna("")

        # --- Detalle Gastos ---
        columnas_gastos = ["Fecha Completa", "Producto", "Cantidad", "Total Gastado", "Método Pago"]
        df_gastos = pd.DataFrame(gastos_lista, columns=columnas_gastos)
        df_gastos["Fecha"] = pd.to_datetime(df_gastos["Fecha Completa"]).dt.strftime("%d/%m/%Y %H:%M")
        df_gastos = df_gastos[["Fecha", "Producto", "Cantidad", "Total Gastado", "Método Pago"]]

        # --- Escribir Excel ---
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                df_ventas.to_excel(writer, sheet_name='Detalle de Ventas', index=False)
                df_gastos.to_excel(writer, sheet_name='Detalle de Gastos', index=False)
                
                # Ajustar anchos
                workbook = writer.book
                workbook['Resumen'].column_dimensions['A'].width = 25
                workbook['Resumen'].column_dimensions['B'].width = 25
                for col_letter in ['B', 'E', 'F']: workbook['Detalle de Ventas'].column_dimensions[col_letter].width = 25
                for col_letter in ['A', 'C', 'D']: workbook['Detalle de Ventas'].column_dimensions[col_letter].width = 15
                for col_letter in ['A', 'D', 'E']: workbook['Detalle de Gastos'].column_dimensions[col_letter].width = 15
                for col_letter in ['B']: workbook['Detalle de Gastos'].column_dimensions[col_letter].width = 30
            
            messagebox.showinfo("Reporte Guardado", f"El reporte histórico se ha guardado en:\n{os.path.abspath(filename)}")
        except Exception as e:
            messagebox.showerror("Error al Exportar", f"No se pudo guardar el reporte Excel. ¿Quizás el archivo está abierto?\nError: {e}")


    # ------------------------------------------------
    # PANTALLA DE CAJA (MODIFICADA)
    # ------------------------------------------------
    def pantalla_caja(self):
        self.limpiar_panel()
        if not self.caja_abierta:
            tk.Label(self.panel, text="Caja Cerrada", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
            tk.Label(self.panel, text="La caja está cerrada. Debe abrirla para empezar a registrar ventas.", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(pady=10, anchor="w", padx=20)
            caja_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); caja_frame.pack(pady=20, padx=20, fill="x")
            tk.Label(caja_frame, text="Monto inicial en caja:", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(side="left", padx=10)
            self.entry_monto_inicial = tk.Entry(caja_frame, font=self.FONT_LABEL, relief="solid", borderwidth=1, width=15)
            self.entry_monto_inicial.insert(0, "0.0"); self.entry_monto_inicial.pack(side="left", ipady=5)
            btn_abrir = self.crear_boton_estilizado(caja_frame, "Abrir Caja", self.COLOR_BOTON_OK, self.accion_abrir_caja, width=15)
            btn_abrir.pack(side="left", padx=20)
        else:
            tk.Label(self.panel, text="Gestión de Caja (Abierta)", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=20, anchor="w")
            
            (total_ventas_netas, total_descuentos) = get_totales_ventas_por_sesion(self.sesion_id)
            total_ventas_brutas = total_ventas_netas + total_descuentos
            total_gastos = get_total_gastos_por_sesion(self.sesion_id)
            resumen_gastos = get_resumen_gastos_por_sesion(self.sesion_id)
            total_gastos_efectivo = next((total for metodo, total in resumen_gastos if metodo == "Efectivo"), 0.0)
            balance_neto = total_ventas_netas - total_gastos
            total_en_caja = (self.sesion_monto_inicial + total_ventas_netas) - total_gastos_efectivo
            
            resumen_frame = tk.Frame(self.panel, bg="#FFFFFF", relief="solid", borderwidth=1)
            resumen_frame.pack(fill="x", pady=10, padx=20)
            
            def crear_fila(label_texto, valor_texto, color_valor=self.COLOR_TEXTO, font_valor=None):
                if font_valor is None: font_valor = self.FONT_LABEL
                frame = tk.Frame(resumen_frame, bg="#FFFFFF")
                frame.pack(fill="x", padx=20, pady=8)
                tk.Label(frame, text=label_texto, font=self.FONT_LABEL, bg="#FFFFFF", fg=self.COLOR_TEXTO).pack(side="left")
                tk.Label(frame, text=valor_texto, font=font_valor, bg="#FFFFFF", fg=color_valor).pack(side="right")

            crear_fila("Caja abierta desde:", self.sesion_fecha_apertura)
            crear_fila("Monto Inicial:", f"${self.sesion_monto_inicial:.2f}")
            ttk.Separator(resumen_frame, orient="horizontal").pack(fill="x", padx=20, pady=5)
            crear_fila("Total Ventas Brutas:", f"${total_ventas_brutas:.2f}")
            crear_fila("Total Descuentos:", f"(${total_descuentos:.2f})", self.COLOR_BOTON_DEL)
            crear_fila("Total Ventas Netas:", f"${total_ventas_netas:.2f}", self.COLOR_BOTON_OK, ("Segoe UI", 12, "bold"))
            ttk.Separator(resumen_frame, orient="horizontal").pack(fill="x", padx=20, pady=5)
            crear_fila("Total Gastos:", f"(${total_gastos:.2f})", self.COLOR_BOTON_DEL, ("Segoe UI", 12, "bold"))
            ttk.Separator(resumen_frame, orient="horizontal").pack(fill="x", padx=20, pady=5)
            crear_fila("Balance Neto (Ventas - Gastos):", f"${balance_neto:.2f}", self.COLOR_TITULO, ("Segoe UI", 14, "bold"))
            crear_fila("Total en Caja (Estimado):", f"${total_en_caja:.2f}", self.COLOR_BOTON_EDIT, ("Segoe UI", 14, "bold"))
            
            btn_frame = tk.Frame(self.panel, bg=self.COLOR_PANEL); btn_frame.pack(pady=20, fill="x", padx=20)
            btn_actualizar = self.crear_boton_estilizado(btn_frame, "Actualizar", self.COLOR_BOTON_EDIT, self.pantalla_caja, width=15)
            btn_actualizar.pack(side="left")
            btn_cerrar = self.crear_boton_estilizado(btn_frame, "Cerrar Caja", self.COLOR_BOTON_DEL, self.accion_cerrar_caja, width=15)
            btn_cerrar.pack(side="right")
            
    def accion_abrir_caja(self):
        try:
            monto_inicial = float(self.entry_monto_inicial.get())
        except:
            messagebox.showerror("Error", "El monto inicial debe ser un número.")
            return
            
        self.sesion_id = abrir_caja(monto_inicial)
        self.caja_abierta = True
        self.sesion_monto_inicial = monto_inicial
        sesion_abierta = get_ultima_sesion_abierta()
        self.sesion_fecha_apertura = sesion_abierta[1]
        
        self.actualizar_estado_menu()
        self.pantalla_inicio() # <-- Ir al Dashboard al abrir
        messagebox.showinfo("Caja Abierta", f"Se ha iniciado la caja con ${monto_inicial:.2f}")

    def accion_cerrar_caja(self):
        if not messagebox.askyesno("Confirmar Cierre", "¿Está seguro que desea cerrar la caja?\nEsta acción generará el reporte final y bloqueará las ventas."):
            return
            
        (total_ventas_netas, total_descuentos) = get_totales_ventas_por_sesion(self.sesion_id)
        ventas_lista = get_ventas_detalladas_por_sesion(self.sesion_id)
        total_gastos = get_total_gastos_por_sesion(self.sesion_id)
        gastos_lista = get_gastos_detallados_por_sesion(self.sesion_id)
        fecha_apertura_guardada = self.sesion_fecha_apertura
        sesion_id_guardada = self.sesion_id
        
        cerrar_caja(self.sesion_id, total_ventas_netas, total_descuentos)
        
        self.caja_abierta = False
        self.sesion_id = None
        self.sesion_fecha_apertura = None
        self.sesion_monto_inicial = 0.0
        
        self.actualizar_estado_menu()
        
        try:
            filepath = self.exportar_reporte_excel(sesion_id_guardada, fecha_apertura_guardada, ventas_lista, gastos_lista, total_ventas_netas, total_descuentos, total_gastos)
            messagebox.showinfo("Reporte Guardado", f"El reporte de cierre se ha guardado en:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error al Exportar", f"No se pudo guardar el reporte Excel.\nError: {e}")
        
        self.mostrar_reporte_cierre(fecha_apertura_guardada, ventas_lista, gastos_lista, total_ventas_netas, total_descuentos, total_gastos)

    # --- MODIFICADO: Ahora incluye 'cliente' ---
    def exportar_reporte_excel(self, sesion_id: int, fecha_apertura: str, ventas_lista: list, gastos_lista: list, total_neto: float, total_descuentos: float, total_gastos: float) -> str:
        REPORTS_DIR = "reportes"; os.makedirs(REPORTS_DIR, exist_ok=True)
        fecha_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = os.path.join(REPORTS_DIR, f"reporte_caja_sesion_{sesion_id}_{fecha_str}.xlsx")

        total_ventas_brutas = total_neto + total_descuentos
        resumen_gastos = get_resumen_gastos_por_sesion(sesion_id)
        total_gastos_efectivo = next((total for metodo, total in resumen_gastos if metodo == "Efectivo"), 0.0)
        balance_neto = total_neto - total_gastos
        total_en_caja = (self.sesion_monto_inicial + total_neto) - total_gastos_efectivo
        
        resumen_data = {
            "Concepto": ["Fecha Apertura", "Fecha Cierre", "Monto Inicial", "Total Ventas Brutas", "Total Descuentos", "Total Ventas Netas", "Total Gastos", "Balance Neto (Ventas - Gastos)", "Total en Caja (Estimado)"],
            "Valor": [fecha_apertura, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.sesion_monto_inicial, total_ventas_brutas, total_descuentos, total_neto, total_gastos, balance_neto, total_en_caja]
        }
        df_resumen = pd.DataFrame(resumen_data)

        columnas_ventas = ["Fecha Completa", "Total Neto", "Método Pago", "Descuento", "Motivo Descuento", "Cliente"]
        df_ventas = pd.DataFrame(ventas_lista, columns=columnas_ventas)
        df_ventas["Hora"] = pd.to_datetime(df_ventas["Fecha Completa"]).dt.strftime("%H:%M:%S")
        df_ventas = df_ventas[["Hora", "Cliente", "Total Neto", "Método Pago", "Descuento", "Motivo Descuento"]]
        df_ventas["Motivo Descuento"] = df_ventas["Motivo Descuento"].fillna("")

        columnas_gastos = ["Fecha Completa", "Producto", "Cantidad", "Total Gastado", "Método Pago"]
        df_gastos = pd.DataFrame(gastos_lista, columns=columnas_gastos)
        df_gastos["Hora"] = pd.to_datetime(df_gastos["Fecha Completa"]).dt.strftime("%H:%M:%S")
        df_gastos = df_gastos[["Hora", "Producto", "Cantidad", "Total Gastado", "Método Pago"]]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            df_ventas.to_excel(writer, sheet_name='Detalle de Ventas', index=False)
            df_gastos.to_excel(writer, sheet_name='Detalle de Gastos', index=False)
            try:
                workbook = writer.book
                workbook['Resumen'].column_dimensions['A'].width = 25; workbook['Resumen'].column_dimensions['B'].width = 25
                sheet_ventas = workbook['Detalle de Ventas']
                sheet_ventas.column_dimensions['A'].width = 12; sheet_ventas.column_dimensions['B'].width = 25; sheet_ventas.column_dimensions['C'].width = 15
                sheet_ventas.column_dimensions['D'].width = 15; sheet_ventas.column_dimensions['E'].width = 15; sheet_ventas.column_dimensions['F'].width = 30
                sheet_gastos = workbook['Detalle de Gastos']
                sheet_gastos.column_dimensions['A'].width = 12; sheet_gastos.column_dimensions['B'].width = 30; sheet_gastos.column_dimensions['C'].width = 10
                sheet_gastos.column_dimensions['D'].width = 15; sheet_gastos.column_dimensions['E'].width = 15
            except Exception as e:
                print(f"No se pudo ajustar el ancho de columnas: {e}")
        return os.path.abspath(filename)

    # --- MODIFICADO: Ahora incluye 'cliente' ---
    def mostrar_reporte_cierre(self, fecha_apertura_reporte: str, ventas_lista: list, gastos_lista: list, total_neto: float, total_descuento: float, total_gastos: float):
        self.limpiar_panel()
        tk.Label(self.panel, text="Reporte de Cierre de Caja", font=self.FONT_TITULO, bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(pady=10, anchor="w")
        fecha_cierre = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(self.panel, text=f"Sesión: {fecha_apertura_reporte}  ---  {fecha_cierre}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="w", padx=20)
        notebook = ttk.Notebook(self.panel); notebook.pack(fill="both", expand=True, pady=10, padx=20)
        frame_ventas = tk.Frame(notebook, bg=self.COLOR_PANEL); frame_gastos = tk.Frame(notebook, bg=self.COLOR_PANEL)
        notebook.add(frame_ventas, text='Detalle de Ventas'); notebook.add(frame_gastos, text='Detalle de Gastos')

        columnas_ventas = ("hora", "cliente", "total", "metodo", "descuento", "motivo")
        tree_ventas = ttk.Treeview(frame_ventas, columns=columnas_ventas, show="headings", style="Treeview")
        tree_ventas.heading("hora", text="Hora"); tree_ventas.heading("cliente", text="Cliente"); tree_ventas.heading("total", text="Total Neto")
        tree_ventas.heading("metodo", text="Método Pago"); tree_ventas.heading("descuento", text="Descuento"); tree_ventas.heading("motivo", text="Motivo")
        tree_ventas.column("hora", width=100); tree_ventas.column("cliente", width=150); tree_ventas.column("total", width=100)
        tree_ventas.column("metodo", width=120); tree_ventas.column("descuento", width=100); tree_ventas.column("motivo", width=150)
        tree_ventas.pack(side="left", fill="both", expand=True)
        scroll_ventas = ttk.Scrollbar(frame_ventas, orient="vertical", command=tree_ventas.yview)
        tree_ventas.configure(yscroll=scroll_ventas.set); scroll_ventas.pack(side="right", fill="y")
        
        for (fecha, total, metodo, descuento, motivo, cliente) in ventas_lista:
            hora = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            tree_ventas.insert("", "end", values=(hora, cliente, f"${total:.2f}", metodo, f"${descuento:.2f}", motivo if motivo else ""))

        tree_gastos = ttk.Treeview(frame_gastos, columns=("hora", "producto", "cant", "total", "metodo"), show="headings", style="Treeview")
        tree_gastos.heading("hora", text="Hora"); tree_gastos.heading("producto", text="Producto"); tree_gastos.heading("cant", text="Cantidad")
        tree_gastos.heading("total", text="Total"); tree_gastos.heading("metodo", text="Pagado con")
        tree_gastos.column("hora", width=100); tree_gastos.column("producto", width=250); tree_gastos.column("cant", width=80)
        tree_gastos.column("total", width=100); tree_gastos.column("metodo", width=120)
        tree_gastos.pack(side="left", fill="both", expand=True)
        scroll_gastos = ttk.Scrollbar(frame_gastos, orient="vertical", command=tree_gastos.yview)
        tree_gastos.configure(yscroll=scroll_gastos.set); scroll_gastos.pack(side="right", fill="y")

        for (fecha, producto, cantidad, total, metodo) in gastos_lista:
            hora = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            tree_gastos.insert("", "end", values=(hora, producto, cantidad, f"${total:.2f}", metodo))
            
        total_bruto = total_neto + total_descuento; balance_neto = total_neto - total_gastos
        tk.Label(self.panel, text=f"Total Ventas Brutas: ${total_bruto:.2f}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO).pack(anchor="e", padx=20)
        tk.Label(self.panel, text=f"Total Descuentos: ${total_descuento:.2f}", font=self.FONT_LABEL, bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_DEL).pack(anchor="e", padx=20)
        tk.Label(self.panel, text=f"Total Ventas Netas: ${total_neto:.2f}", font=("Segoe UI", 14, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_OK).pack(anchor="e", padx=20)
        tk.Label(self.panel, text=f"Total Gastos: ${total_gastos:.2f}", font=("Segoe UI", 14, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_BOTON_DEL).pack(anchor="e", padx=20)
        tk.Label(self.panel, text=f"BALANCE NETO (VENTAS - GASTOS): ${balance_neto:.2f}", font=("Segoe UI", 16, "bold"), bg=self.COLOR_PANEL, fg=self.COLOR_TITULO).pack(anchor="e", padx=20, pady=5)
        btn_volver = self.crear_boton_estilizado(self.panel, "Aceptar", self.COLOR_BOTON_EDIT, self.pantalla_caja)
        btn_volver.pack(pady=10)