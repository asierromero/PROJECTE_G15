import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import queue
import time
from datetime import datetime, timedelta
import csv
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d import Axes3D
from collections import deque
import math
from enum import Enum

# ENUMERACIONES Y CONSTANTES
class TipoEvento(Enum):
    ALARMA = "alarma"
    COMANDO = "comando"
    OBSERVACION = "observacion"

class TipoSensor(Enum):
    DHT = "DHT"
    RADAR = "RADAR"
    ORBITA = "ORBITA"


# Constantes de configuración
# NOTA: Estos valores están optimizados para un entorno de desarrollo. En un sistema profesional, los límites serían mayores y gestionados dinámicamente.
CHECKSUM_MOD = 256
MAX_PUNTOS_GRAFICA = 500
MAX_PUNTOS_RADAR = 500
MAX_PUNTOS_ORBITA = 500


# ======================= CONFIGURACIÓN =======================

class EstacionTierraSatelite:
    def __init__(self, root):
        """Inicializa la estación de tierra con la ventana principal"""
        self.root = root
        self.root.title("ESTACIÓN DE TIERRA - SISTEMA SATELITAL")
        self.root.geometry("1400x900")
       
        # VARIABLES DE COMUNICACIÓN SERIAL
        self.puerto_serial = None
        self.recibiendo_datos = False
        self.hilo_serial = None
        self.cola_datos = queue.Queue()
        self.cola_comandos = queue.Queue()
       
        # VARIABLES PARA ALMACENAR DATOS
        self.temperaturas = deque(maxlen=MAX_PUNTOS_GRAFICA)
        self.humedades = deque(maxlen=MAX_PUNTOS_GRAFICA)
        self.distancias_radar = deque(maxlen=MAX_PUNTOS_GRAFICA)
        self.angulos_radar = deque(maxlen=MAX_PUNTOS_GRAFICA)
        self.tiempos_orbita = deque(maxlen=MAX_PUNTOS_ORBITA)
        self.posiciones_orbita = deque(maxlen=MAX_PUNTOS_ORBITA)
        self.marcas_tiempo = deque(maxlen=MAX_PUNTOS_GRAFICA)
       
        # Buffer para medias
        self.buffer_temp_media = deque(maxlen=10)
        self.buffer_hum_media = deque(maxlen=10)
        self.medidas_temp_media = deque(maxlen=100)
        self.medidas_hum_media = deque(maxlen=100)
       
        # VARIABLES DE CONTROL
        self.calculo_media_en_satelite = tk.BooleanVar(value=True)
        self.dht_activo = tk.BooleanVar(value=True)
        self.radar_activo = tk.BooleanVar(value=True)
        self.orbita_activa = tk.BooleanVar(value=True)
        self.modo_radar_rastreo = tk.BooleanVar(value=True)
        self.alarma_activada = tk.BooleanVar(value=False)
       
        # Configuración del sistema
        self.intervalo_dht_ms = tk.IntVar(value=2000)
        self.intervalo_radar_ms = tk.IntVar(value=1000)
        self.intervalo_orbita_ms = tk.IntVar(value=1000)
        self.limite_temperatura_max = tk.DoubleVar(value=30.0)
        self.limite_humedad_max = tk.DoubleVar(value=80.0)
       
        # ALARMAS
        self.contador_temp_supera_limite = 0
        self.contador_hum_supera_limite = 0
        self.alarma_temp_activada = False
        self.alarma_hum_activada = False
       
        # ESTADO DE ERROR DE SENSORES
        self.error_dht = False
        self.error_radar = False
        self.error_orbita = False
        self.ultimo_dht_valido = None
        self.ultimo_radar_valido = None
        self.ultimo_orbita_valido = None
       
        # TIEMPOS DE COMUNICACIÓN
        self.ultima_comunicacion = time.time()
        self.tiempo_espera_comunicacion = 10
       
        # REGISTRO DE EVENTOS
        self.eventos_registrados = []
        self.eventos_filtrados = []
       
        # PUNTOS DEL RADAR
        self.puntos_radar = []
       
        # PARÁMETROS ÓRBITA
        self.angulo_orbita_actual = 0
        self.velocidad_orbita = 0.05
        self.animacion_orbita_activa = False
       
        # INICIALIZACIÓN DEL SISTEMA
        self.directorios()
        self.configurar_graficas()
        self.configurar_interfaz()
        self.actualizaciones_periodicas()
       
        self.registrar_evento(TipoEvento.COMANDO, "Sistema iniciado")


# CONFIGURACIÓN DE GRÁFICAS ______________________________________

    def configurar_graficas(self):
        """Configura todas las gráficas y visualizaciones del sistema"""

        #TEMPERATURA
        # Gráfica de temperatura en tiempo real
        self.figura_temp_real = Figure(figsize=(6, 3), dpi=100, facecolor='#f8f9fa')
        self.eje_temp_real = self.figura_temp_real.add_subplot(111)
       
        self.eje_temp_real.set_xlabel('Tiempo (s)', fontsize=9)
        self.eje_temp_real.set_ylabel('Temperatura (°C)', fontsize=9)
        self.eje_temp_real.set_title('Temperatura en Tiempo Real', fontsize=10, fontweight='bold')
        self.eje_temp_real.grid(True, alpha=0.3)
       
        self.linea_temp_real, = self.eje_temp_real.plot([], [], 'r-', linewidth=2, marker='o', markersize=3)
        self.linea_limite_temp, = self.eje_temp_real.plot([], [], 'r--', linewidth=1.5, alpha=0.7, label='Límite')
       
        self.figura_temp_real.tight_layout()
       
        # Gráfica de media de temperaturas
        self.figura_temp_media = Figure(figsize=(6, 3), dpi=100, facecolor='#f8f9fa')
        self.eje_temp_media = self.figura_temp_media.add_subplot(111)
       
        self.eje_temp_media.set_xlabel('Tiempo (s)', fontsize=9)
        self.eje_temp_media.set_ylabel('Temperatura Media (°C)', fontsize=9)
        self.eje_temp_media.set_title('Media de las Últimas 10 Temperaturas', fontsize=10, fontweight='bold')
        self.eje_temp_media.grid(True, alpha=0.3)
       
        self.linea_temp_media, = self.eje_temp_media.plot([], [], 'b-', linewidth=2, marker='s', markersize=3)
        self.linea_limite_temp_media, = self.eje_temp_media.plot([], [], 'r--', linewidth=1.5, alpha=0.7)
       
        self.figura_temp_media.tight_layout()
       
        #HUMEDAD
        # Gráfica de humedad en tiempo real
        self.figura_hum_real = Figure(figsize=(6, 3), dpi=100, facecolor='#f8f9fa')
        self.eje_hum_real = self.figura_hum_real.add_subplot(111)
       
        self.eje_hum_real.set_xlabel('Tiempo (s)', fontsize=9)
        self.eje_hum_real.set_ylabel('Humedad (%)', fontsize=9)
        self.eje_hum_real.set_title('Humedad en Tiempo Real', fontsize=10, fontweight='bold')
        self.eje_hum_real.grid(True, alpha=0.3)
       
        self.linea_hum_real, = self.eje_hum_real.plot([], [], 'g-', linewidth=2, marker='^', markersize=3)
        self.linea_limite_hum, = self.eje_hum_real.plot([], [], 'g--', linewidth=1.5, alpha=0.7, label='Límite')
       
        self.figura_hum_real.tight_layout()
       
        # Gráfica de media de humedades
        self.figura_hum_media = Figure(figsize=(6, 3), dpi=100, facecolor='#f8f9fa')
        self.eje_hum_media = self.figura_hum_media.add_subplot(111)
       
        self.eje_hum_media.set_xlabel('Tiempo (s)', fontsize=9)
        self.eje_hum_media.set_ylabel('Humedad Media (%)', fontsize=9)
        self.eje_hum_media.set_title('Media de las Últimas 10 Humedades', fontsize=10, fontweight='bold')
        self.eje_hum_media.grid(True, alpha=0.3)
       
        self.linea_hum_media, = self.eje_hum_media.plot([], [], 'c-', linewidth=2, marker='d', markersize=3)
        self.linea_limite_hum_media, = self.eje_hum_media.plot([], [], 'g--', linewidth=1.5, alpha=0.7)
       
        self.figura_hum_media.tight_layout()
       
        #RADAR
        # Gráfica radar polar
        self.figura_radar_polar = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.eje_radar_polar = self.figura_radar_polar.add_subplot(111, polar=True)
       
        self.eje_radar_polar.set_theta_zero_location('N')
        self.eje_radar_polar.set_theta_direction(-1)
        self.eje_radar_polar.set_thetamin(0)
        self.eje_radar_polar.set_thetamax(180)
        self.eje_radar_polar.set_ylim(0, 400)
        self.eje_radar_polar.set_title('Radar - Vista Polar (0-180°)', fontsize=11, fontweight='bold', pad=15)
        self.eje_radar_polar.grid(True, alpha=0.3)
       
        angulos_principales = [0, 45, 90, 135, 180]
        self.eje_radar_polar.set_xticks(np.radians(angulos_principales))
        self.eje_radar_polar.set_xticklabels(['0°', '45°', '90°', '135°', '180°'])
       
        for distancia in [100, 200, 300, 400]:
            self.eje_radar_polar.plot(np.linspace(0, np.pi, 100), [distancia]*100, 'gray',
                                     alpha=0.2, linewidth=0.5)
       
        self.linea_radar_polar, = self.eje_radar_polar.plot([], [], 'r-', linewidth=2, alpha=0.7)
        self.dispersor_radar_polar = self.eje_radar_polar.scatter([], [], c='red', s=20, alpha=0.7, zorder=10)
       
        #ÓRBITA
        # Gráfica órbita 3D
        self.figura_orbita_3d = Figure(figsize=(6, 5), dpi=100, facecolor='black')
        self.eje_orbita_3d = self.figura_orbita_3d.add_subplot(111, projection='3d')
       
        self.eje_orbita_3d.set_facecolor('black')
        self.eje_orbita_3d.set_xlim(-2, 2)
        self.eje_orbita_3d.set_ylim(-2, 2)
        self.eje_orbita_3d.set_zlim(-2, 2)
       
        self.eje_orbita_3d.set_xticks([])
        self.eje_orbita_3d.set_yticks([])
        self.eje_orbita_3d.set_zticks([])
       
        self.eje_orbita_3d.view_init(elev=30, azim=45)
        self.eje_orbita_3d.set_title('Órbita Satelital 3D', fontsize=12, fontweight='bold', color='white')
       
        # Crear representación de la Tierra
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 30)
        x = 0.5 * np.outer(np.cos(u), np.sin(v))
        y = 0.5 * np.outer(np.sin(u), np.sin(v))
        z = 0.5 * np.outer(np.ones(np.size(u)), np.cos(v))
       
        self.eje_orbita_3d.plot_surface(x, y, z, color='#3498db', alpha=0.8)
       
        # Crear trayectoria orbital
        theta = np.linspace(0, 2 * np.pi, 100)
        orbit_x = 1.5 * np.cos(theta)
        orbit_y = 1.5 * np.sin(theta)
        orbit_z = 0.3 * np.sin(2*theta)
       
        self.linea_orbita_3d, = self.eje_orbita_3d.plot(orbit_x, orbit_y, orbit_z, 'cyan',
                                                       alpha=0.3, linewidth=1, linestyle='--')
       
        # Satélite
        self.satelite_3d, = self.eje_orbita_3d.plot([], [], [], 'ro', markersize=8,
                                                  markeredgecolor='white', markeredgewidth=1.5)
       
        # Trayectoria
        self.linea_trayectoria_3d, = self.eje_orbita_3d.plot([], [], [], 'r-', alpha=0.3, linewidth=1)
       
       
        # Estrellas - visualización más realista
        for _ in range(100): # Usamos _ porque no importa el valor del contador, solo repetir.
            x = np.random.uniform(-3, 3)
            y = np.random.uniform(-3, 3)
            z = np.random.uniform(-3, 3)
            medida_estrellas = np.random.uniform(0.5, 2)
            self.eje_orbita_3d.plot([x], [y], [z], 'w.', markersize=medida_estrellas, alpha=np.random.uniform(0.3, 0.8))
           

# CONFIGURACIÓN INICAL ______________________________________________

    def directorios(self):
        """Crea los directorios necesarios para el sistema"""
        directorios = ['logs', 'data', 'exports']
        for nombre_dir in directorios:
            if not os.path.exists(nombre_dir):
                os.makedirs(nombre_dir)

    def configurar_interfaz(self):
        """Configura la interfaz gráfica principal"""
        self.cuaderno = ttk.Notebook(self.root)
        self.cuaderno.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Pestañas en la parte superior
        self.solapa_control()
        self.solapa_graficas()
        self.solapa_radar()
        self.solapa_orbita()
        self.solapa_eventos()
        self.solapa_observaciones()
       
        self.barra_estado()
        self.consola()

    def solapa_control(self):
        """Crea la solapa de control, la principal"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Control")
       
        panel_dividido = ttk.PanedWindow(solapa, orient=tk.HORIZONTAL) # Dividido en 2
        panel_dividido.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Sección izquierda: Conexión y control general
        seccion_izquierda = ttk.Frame(panel_dividido)
        panel_dividido.add(seccion_izquierda, weight=0)
       
        # Sección derecha: Datos
        seccion_derecha = ttk.Frame(panel_dividido)
        panel_dividido.add(seccion_derecha, weight=2)
       
    # SECCIÓN IZQUIERDA
        # Frame de conexión
        marco_conexion = ttk.LabelFrame(seccion_izquierda, text="CONEXIÓN", padding=10)
        marco_conexion.pack(fill=tk.X, padx=5, pady=5)
       
        ttk.Label(marco_conexion, text="Puerto:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
       
        self.combo_puertos = ttk.Combobox(marco_conexion, width=15, state="readonly")
        self.combo_puertos.grid(row=0, column=1, padx=5, pady=5)
       
        btn_refrescar = ttk.Button(marco_conexion, text="Buscar", command=self.buscar_puertos_disponibles, width=8)
        btn_refrescar.grid(row=0, column=2, padx=5, pady=5)
       
        btn_conectar = ttk.Button(marco_conexion, text="Conectar", command=self.conectar_serial, width=8)
        btn_conectar.grid(row=0, column=3, padx=5, pady=5)
       
        btn_desconectar = ttk.Button(marco_conexion, text="Desconectar", command=self.desconectar_serial, width=17)
        btn_desconectar.grid(row=0, column=4,  padx=5, pady=5)
       
        # Frame de control general
        controles_general = ttk.LabelFrame(seccion_izquierda, text="CONTROL GENERAL", padding=10)
        controles_general.pack(fill=tk.X, padx=5, pady=5)
       
        btn_parar_todo = ttk.Button(controles_general, text="PARAR TODO", command=self.detener_todos_sensores)
        btn_parar_todo.pack(fill=tk.X, pady=2)
       
        btn_reanudar_todo = ttk.Button(controles_general, text="REANUDAR TODO", command=self.reanudar_todos_sensores)
        btn_reanudar_todo.pack(fill=tk.X, pady=2)
       
        # Frame de métricas (debajo de control general)
        marco_metricas = ttk.LabelFrame(seccion_izquierda, text="MÉTRICAS EN TIEMPO REAL", padding=10)
        marco_metricas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Grid de métricas
        metricas = [
       
            ("Temperatura", "temperatura_actual", "°C", "#e74c3c", 0, 0),
            ("Humedad", "humedad_actual", "%", "#3498db", 0, 1),
            ("Distancia", "distancia_actual", "cm", "#2ecc71", 5, 0),
            ("Ángulo", "angulo_actual", "°", "#e67e22", 5, 1),
            ("Media Temp", "temperatura_media", "°C", "#9b59b6", 1, 0),
            ("Media Hum", "humedad_media", "%", "#1abc9c", 1, 1),
            ("Estado DHT", "estado_dht", "", "#27ae60", 6, 0),
            ("Estado Radar", "estado_radar", "", "#34495e", 6, 1),
            ("Temp Mín", "temperatura_min", "°C", "#95a5a6", 2, 0),
            ("Temp Máx", "temperatura_max", "°C", "#95a5a6", 3, 0),
            ("Hum Mín", "humedad_min", "%", "#95a5a6", 2, 1),
            ("Hum Máx", "humedad_max", "%", "#95a5a6", 3, 1)
           
        ]
       
        self.etiquetas_metricas = {}
       
        for texto, clave, unidad, color, fila, col in metricas:
            frame = ttk.Frame(marco_metricas)
           
            frame.grid(row=fila, column=col, padx=5, pady=5, sticky="ns") # ns para centrar
           
            lbl_nombre = ttk.Label(frame, text=texto, font=('Arial', 8))
            lbl_nombre.pack(anchor=tk.CENTER)
           
            frame_valor = ttk.Frame(frame)
            frame_valor.pack(anchor=tk.CENTER)
           
            # Valor
            lbl_valor = ttk.Label(frame_valor, text="--",
                                font=('Arial', 12, 'bold'),
                                foreground=color)
            lbl_valor.pack(side=tk.LEFT)
           
            # Unidad al lado
            if unidad:
                ttk.Label(frame_valor, text=unidad,
                         font=('Arial', 8)).pack(side=tk.LEFT, padx=(2, 0))
           
            self.etiquetas_metricas[clave] = lbl_valor
       
        for i in range(2): # COLUMNAS
            marco_metricas.grid_columnconfigure(i, weight=1, uniform="metric_col")
       
        for i in range(7):  # FILAS
            marco_metricas.grid_rowconfigure(i, weight=1)
       
    # SECCIÓN DERECHA
        # Frame de datos recibidos
        marco_datos = ttk.LabelFrame(seccion_derecha, text="ÚLTIMOS DATOS RECIBIDOS", padding=10)
        marco_datos.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        columnas = ("Hora", "Sensor", "Valor 1", "Valor 2", "Estado")
        self.tabla_datos_recibidos = ttk.Treeview(marco_datos, columns=columnas, show="headings", height=6)
       
        anchos = [70, 70, 80, 80, 70]
        for col, ancho in zip(columnas, anchos):
            self.tabla_datos_recibidos.heading(col, text=col)
            self.tabla_datos_recibidos.column(col, width=ancho)
       
        scrollbar = ttk.Scrollbar(marco_datos, orient=tk.VERTICAL, command=self.tabla_datos_recibidos.yview)
        self.tabla_datos_recibidos.configure(yscrollcommand=scrollbar.set)
       
        self.tabla_datos_recibidos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def solapa_graficas(self):
        """Crea la solapa de gráficas optimizada"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Gráficas")
       
        panel_principal = ttk.PanedWindow(solapa, orient=tk.VERTICAL) # Panel divido
        panel_principal.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        panel_temperatura = ttk.Frame(panel_principal) # Panel superior para temperatura
        panel_principal.add(panel_temperatura, weight=1)
       
        panel_humedad = ttk.Frame(panel_principal) # Panel inferior para humedad
        panel_principal.add(panel_humedad, weight=1)
       
        # PANEL TEMPERATURA
        controles_temp = ttk.LabelFrame(panel_temperatura, text="CONTROLES TEMPERATURA", padding=10)
        controles_temp.pack(fill=tk.X, padx=5, pady=5)
       
        # Controles para sensor DHT (temperatura)
        control_dht_temp = ttk.Frame(controles_temp)
        control_dht_temp.pack(fill=tk.X, pady=2)
       
        ttk.Label(control_dht_temp, text="Sensor DHT:", width=10).pack(side=tk.LEFT)
        ttk.Button(control_dht_temp, text="DETENER",
                  command=lambda: self.detener_sensor(TipoSensor.DHT),
                  width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_dht_temp, text="REANUDAR",
                  command=lambda: self.reanudar_sensor(TipoSensor.DHT),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        ttk.Label(control_dht_temp, text="Intervalo:").pack(side=tk.LEFT, padx=(10,5))
        self.selector_intervalo_dht = ttk.Spinbox(control_dht_temp, from_=500, to=10000,
                                                increment=500, width=6, textvariable=self.intervalo_dht_ms)
        self.selector_intervalo_dht.pack(side=tk.LEFT)
        ttk.Button(control_dht_temp, text="Cambiar",
                  command=lambda: self.cambiar_intervalo_sensor(TipoSensor.DHT),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        # Configuración de límites y medias
        marco_config_temp = ttk.Frame(controles_temp)
        marco_config_temp.pack(fill=tk.X, pady=2)
       
        # Cálculo de medias
        frame_media = ttk.Frame(marco_config_temp)
        frame_media.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame_media, text="Cálculo de medias:").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_media, text="Satélite", variable=self.calculo_media_en_satelite,
                       value=True, command=self.cambiar_modo_calculo_media).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(frame_media, text="Tierra", variable=self.calculo_media_en_satelite,
                       value=False, command=self.cambiar_modo_calculo_media).pack(side=tk.LEFT)
       
        # Límite temperatura
        frame_limite_temp = ttk.Frame(marco_config_temp)
        frame_limite_temp.pack(side=tk.LEFT, padx=20)
        ttk.Label(frame_limite_temp, text="Límite temp:").pack(side=tk.LEFT)
        self.selector_limite_temp = ttk.Spinbox(frame_limite_temp, from_=0, to=100, increment=0.5,
                                              width=8, textvariable=self.limite_temperatura_max)
        self.selector_limite_temp.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame_limite_temp, text="°C").pack(side=tk.LEFT)
        ttk.Button(frame_limite_temp, text="Aplicar", width=6,
                  command=lambda: self.aplicar_limite_alarma('temperatura')).pack(side=tk.LEFT, padx=5)
       
        # Estado alarma temperatura
        frame_estado_temp = ttk.Frame(marco_config_temp)
        frame_estado_temp.pack(side=tk.LEFT, padx=20)
        ttk.Label(frame_estado_temp, text="Estado:").pack(side=tk.LEFT)
        self.etiqueta_estado_alarma_temp = ttk.Label(frame_estado_temp, text="NORMAL",
                                                   foreground="green", font=('Arial', 9, 'bold'))
        self.etiqueta_estado_alarma_temp.pack(side=tk.LEFT, padx=5)
       
        ttk.Label(frame_estado_temp, text="Superaciones:").pack(side=tk.LEFT, padx=(10,5))
        self.etiqueta_contador_alarma_temp = ttk.Label(frame_estado_temp, text="0",
                                                     font=('Arial', 9, 'bold'))
        self.etiqueta_contador_alarma_temp.pack(side=tk.LEFT)
       
        # Gráficas temperatura
        marco_graficas_temp = ttk.Frame(panel_temperatura)
        marco_graficas_temp.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        marco_graficas_temp.grid_columnconfigure(0, weight=1)
        marco_graficas_temp.grid_columnconfigure(1, weight=1)
        marco_graficas_temp.grid_rowconfigure(0, weight=1)
       
        # Gráfica temperatura tiempo real
        marco_temp_real = ttk.LabelFrame(marco_graficas_temp, text="TEMPERATURA TIEMPO REAL")
        marco_temp_real.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
       
        self.canvas_temp_real = FigureCanvasTkAgg(self.figura_temp_real, marco_temp_real)
        self.canvas_temp_real.get_tk_widget().pack(fill=tk.BOTH, expand=True)
       
        # Gráfica media temperaturas
        marco_temp_media = ttk.LabelFrame(marco_graficas_temp, text="MEDIA TEMPERATURAS")
        marco_temp_media.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)
       
        self.canvas_temp_media = FigureCanvasTkAgg(self.figura_temp_media, marco_temp_media)
        self.canvas_temp_media.get_tk_widget().pack(fill=tk.BOTH, expand=True)
       
        # PANEL HUMEDAD
        controles_hum = ttk.LabelFrame(panel_humedad, text="CONTROLES HUMEDAD", padding=10)
        controles_hum.pack(fill=tk.X, padx=5, pady=5)
       
        # Configuración de límites y medias para humedad
        marco_config_hum = ttk.Frame(controles_hum)
        marco_config_hum.pack(fill=tk.X, pady=2)
       
        # Límite humedad
        frame_limite_hum = ttk.Frame(marco_config_hum)
        frame_limite_hum.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame_limite_hum, text="Límite hum:").pack(side=tk.LEFT)
        self.selector_limite_hum = ttk.Spinbox(frame_limite_hum, from_=0, to=100,
                                             increment=1, width=8, textvariable=self.limite_humedad_max)
        self.selector_limite_hum.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame_limite_hum, text="%").pack(side=tk.LEFT)
        ttk.Button(frame_limite_hum, text="Aplicar", width=6,
                  command=lambda: self.aplicar_limite_alarma('humedad')).pack(side=tk.LEFT, padx=5)
       
        # Estado alarma humedad
        frame_estado_hum = ttk.Frame(marco_config_hum)
        frame_estado_hum.pack(side=tk.LEFT, padx=20)
        ttk.Label(frame_estado_hum, text="Estado:").pack(side=tk.LEFT)
        self.etiqueta_estado_alarma_hum = ttk.Label(frame_estado_hum, text="NORMAL",
                                                  foreground="green", font=('Arial', 9, 'bold'))
        self.etiqueta_estado_alarma_hum.pack(side=tk.LEFT, padx=5)
       
        ttk.Label(frame_estado_hum, text="Superaciones:").pack(side=tk.LEFT, padx=(10,5))
        self.etiqueta_contador_alarma_hum = ttk.Label(frame_estado_hum, text="0",
                                                    font=('Arial', 9, 'bold'))
        self.etiqueta_contador_alarma_hum.pack(side=tk.LEFT)
       
        # Gráficas humedad
        marco_graficas_hum = ttk.Frame(panel_humedad)
        marco_graficas_hum.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        marco_graficas_hum.grid_columnconfigure(0, weight=1)
        marco_graficas_hum.grid_columnconfigure(1, weight=1)
        marco_graficas_hum.grid_rowconfigure(0, weight=1)
       
        # Gráfica humedad tiempo real
        marco_hum_real = ttk.LabelFrame(marco_graficas_hum, text="HUMEDAD TIEMPO REAL")
        marco_hum_real.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
       
        self.canvas_hum_real = FigureCanvasTkAgg(self.figura_hum_real, marco_hum_real)
        self.canvas_hum_real.get_tk_widget().pack(fill=tk.BOTH, expand=True)
       
        # Gráfica media humedades
        marco_hum_media = ttk.LabelFrame(marco_graficas_hum, text="MEDIA HUMEDADES")
        marco_hum_media.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)
       
        self.canvas_hum_media = FigureCanvasTkAgg(self.figura_hum_media, marco_hum_media)
        self.canvas_hum_media.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def solapa_radar(self):
        """Crea la solapa de visualización del radar"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Radar")
       
        panel_dividido = ttk.PanedWindow(solapa, orient=tk.HORIZONTAL)
        panel_dividido.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Panel izquierdo para gráfica
        panel_izquierdo = ttk.Frame(panel_dividido)
        panel_dividido.add(panel_izquierdo, weight=3)
       
        # Panel derecho para controles
        panel_derecho = ttk.Frame(panel_dividido)
        panel_dividido.add(panel_derecho, weight=1)
       
        # Gráfica radar polar
        marco_radar = ttk.LabelFrame(panel_izquierdo, text="RADAR POLAR (0-180°)", padding=10)
        marco_radar.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        self.canvas_radar_polar = FigureCanvasTkAgg(self.figura_radar_polar, marco_radar)
        self.canvas_radar_polar.get_tk_widget().pack(fill=tk.BOTH, expand=True)
       
        # Panel derecho: Datos y controles
        marco_datos = ttk.LabelFrame(panel_derecho, text="DATOS RADAR", padding=10)
        marco_datos.pack(fill=tk.X, padx=5, pady=5)
       
        datos_labels = [
            ("Ángulo:", "angulo_radar", "°"),
            ("Distancia:", "distancia_radar", "cm"),
            ("Objetos:", "objetos_detectados", ""),
            ("Mínima:", "distancia_minima", "cm"),
            ("Máxima:", "distancia_maxima", "cm"),
            ("Media:", "distancia_media", "cm")
        ]
       
        self.etiquetas_radar = {}
       
        for texto, clave, unidad in datos_labels:
            frame = ttk.Frame(marco_datos)
            frame.pack(fill=tk.X, pady=2)
           
            ttk.Label(frame, text=texto, width=12).pack(side=tk.LEFT)
           
            lbl_valor = ttk.Label(frame, text="--", font=('Arial', 9, 'bold'))
            lbl_valor.pack(side=tk.LEFT, padx=5)
           
            if unidad:
                ttk.Label(frame, text=unidad).pack(side=tk.LEFT)
           
            self.etiquetas_radar[clave] = lbl_valor
       
        # Controles de radar
        controles_radar = ttk.LabelFrame(panel_derecho, text="CONTROL RADAR", padding=10)
        controles_radar.pack(fill=tk.X, padx=5, pady=5)
       
        # Controles de parar/reanudar radar
        frame_control_sensor = ttk.Frame(controles_radar)
        frame_control_sensor.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_control_sensor, text="Sensor Radar:", width=12).pack(side=tk.LEFT)
        ttk.Button(frame_control_sensor, text="DETENER",
                  command=lambda: self.detener_sensor(TipoSensor.RADAR),
                  width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_control_sensor, text="REANUDAR",
                  command=lambda: self.reanudar_sensor(TipoSensor.RADAR),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        # Intervalo radar
        frame_intervalo = ttk.Frame(controles_radar)
        frame_intervalo.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_intervalo, text="Intervalo:").pack(side=tk.LEFT)
        self.selector_intervalo_radar = ttk.Spinbox(frame_intervalo, from_=100, to=5000,
                                                  increment=100, width=6, textvariable=self.intervalo_radar_ms)
        self.selector_intervalo_radar.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_intervalo, text="Cambiar",
                  command=lambda: self.cambiar_intervalo_sensor(TipoSensor.RADAR),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        # Modo radar
        frame_modo = ttk.Frame(controles_radar)
        frame_modo.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_modo, text="Modo radar:").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_modo, text="Rastreo", variable=self.modo_radar_rastreo,
                       value=True, command=self.cambiar_modo_radar).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(frame_modo, text="Fijo", variable=self.modo_radar_rastreo,
                       value=False, command=self.cambiar_modo_radar).pack(side=tk.LEFT)
       
        # Ángulo fijo
        frame_angulo = ttk.Frame(controles_radar)
        frame_angulo.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_angulo, text="Ángulo fijo:").pack(side=tk.LEFT)
        self.entrada_angulo_fijo = ttk.Entry(frame_angulo, width=8)
        self.entrada_angulo_fijo.insert(0, "90")
        self.entrada_angulo_fijo.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_angulo, text="Establecer",
                  command=self.establecer_angulo_radar_fijo, width=8).pack(side=tk.LEFT)
       
        # Acciones
        marco_acciones = ttk.LabelFrame(panel_derecho, text="ACCIONES", padding=10)
        marco_acciones.pack(fill=tk.X, padx=5, pady=5)
       
        ttk.Button(marco_acciones, text="Exportar Datos",
                  command=self.exportar_datos_radar).pack(fill=tk.X, pady=2)
       
        ttk.Button(marco_acciones, text="Limpiar Historial",
                  command=self.limpiar_historial_radar).pack(fill=tk.X, pady=2)

    def solapa_orbita(self):
        """Crea la solapa de visualización de la órbita 3D"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Órbita 3D")
       
        panel_dividido = ttk.PanedWindow(solapa, orient=tk.HORIZONTAL)
        panel_dividido.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Panel izquierdo para visualización
        panel_izquierdo = ttk.Frame(panel_dividido)
        panel_dividido.add(panel_izquierdo, weight=3)
       
        # Panel derecho para controles
        panel_derecho = ttk.Frame(panel_dividido)
        panel_dividido.add(panel_derecho, weight=1)
       
        # Visualización órbita 3D
        marco_orbita = ttk.LabelFrame(panel_izquierdo, text="ÓRBITA SATELITAL 3D", padding=10)
        marco_orbita.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        self.canvas_orbita_3d = FigureCanvasTkAgg(self.figura_orbita_3d, marco_orbita)
        self.canvas_orbita_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
       
        # Panel derecho: Parámetros y controles
        marco_parametros = ttk.LabelFrame(panel_derecho, text="PARÁMETROS ÓRBITA", padding=10)
        marco_parametros.pack(fill=tk.X, padx=5, pady=5)
       
        parametros = [
            ("Tiempo:", "tiempo_orbita", "s"),
            ("Posición X:", "posicion_x", "km"),
            ("Posición Y:", "posicion_y", "km"),
            ("Posición Z:", "posicion_z", "km"),
            ("Altitud:", "altitud", "km"),
            ("Velocidad:", "velocidad", "km/s"),
            ("Período:", "periodo", "min"),
            ("Inclinación:", "inclinacion", "°"),
            ("Estado:", "estado_orbita", "")
        ]
       
        self.etiquetas_orbita = {}
       
        for texto, clave, unidad in parametros:
            frame = ttk.Frame(marco_parametros)
            frame.pack(fill=tk.X, pady=2)
           
            ttk.Label(frame, text=texto, width=12).pack(side=tk.LEFT)
           
            lbl_valor = ttk.Label(frame, text="--", font=('Arial', 9))
            lbl_valor.pack(side=tk.LEFT, padx=5)
           
            if unidad:
                ttk.Label(frame, text=unidad).pack(side=tk.LEFT)
           
            self.etiquetas_orbita[clave] = lbl_valor
       
        # Controles de órbita
        controles_orbita = ttk.LabelFrame(panel_derecho, text="CONTROL ÓRBITA", padding=10)
        controles_orbita.pack(fill=tk.X, padx=5, pady=5)
       
        # Controles de parar/reanudar órbita
        frame_control_sensor = ttk.Frame(controles_orbita)
        frame_control_sensor.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_control_sensor, text="Sensor Órbita:", width=12).pack(side=tk.LEFT)
        ttk.Button(frame_control_sensor, text="DETENER",
                  command=lambda: self.detener_sensor(TipoSensor.ORBITA),
                  width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_control_sensor, text="REANUDAR",
                  command=lambda: self.reanudar_sensor(TipoSensor.ORBITA),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        # Intervalo órbita
        frame_intervalo = ttk.Frame(controles_orbita)
        frame_intervalo.pack(fill=tk.X, pady=2)
       
        ttk.Label(frame_intervalo, text="Intervalo:").pack(side=tk.LEFT)
        self.selector_intervalo_orbita = ttk.Spinbox(frame_intervalo, from_=500, to=10000,
                                                   increment=500, width=6, textvariable=self.intervalo_orbita_ms)
        self.selector_intervalo_orbita.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_intervalo, text="Cambiar",
                  command=lambda: self.cambiar_intervalo_sensor(TipoSensor.ORBITA),
                  width=8).pack(side=tk.LEFT, padx=2)
       
        # Controles animación
        marco_animacion = ttk.LabelFrame(panel_derecho, text="CONTROL ANIMACIÓN", padding=10)
        marco_animacion.pack(fill=tk.X, padx=5, pady=5)
       
        ttk.Button(marco_animacion, text="Iniciar Animación",
                  command=self.iniciar_animacion_orbita).pack(fill=tk.X, pady=2)
       
        ttk.Button(marco_animacion, text="Detener Animación",
                  command=self.detener_animacion_orbita).pack(fill=tk.X, pady=2)
       
        # Datos históricos
        marco_historico = ttk.LabelFrame(panel_derecho, text="DATOS HISTÓRICOS", padding=10)
        marco_historico.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        columnas = ("Hora", "Tiempo", "Pos X", "Pos Y", "Pos Z")
        self.tabla_orbita = ttk.Treeview(marco_historico, columns=columnas,
                                       show="headings", height=8)
       
        anchos = [60, 60, 60, 60, 60]
        for col, ancho in zip(columnas, anchos):
            self.tabla_orbita.heading(col, text=col)
            self.tabla_orbita.column(col, width=ancho)
       
        scrollbar = ttk.Scrollbar(marco_historico, orient=tk.VERTICAL,
                                 command=self.tabla_orbita.yview)
        self.tabla_orbita.configure(yscrollcommand=scrollbar.set)
       
        self.tabla_orbita.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def solapa_eventos(self):
        """Crea la solapa de gestión de eventos"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Eventos")
       
        marco_filtros = ttk.LabelFrame(solapa, text="FILTROS", padding=10)
        marco_filtros.pack(fill=tk.X, padx=5, pady=5)
       
        ttk.Label(marco_filtros, text="Fecha:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.fecha_filtro_eventos = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(marco_filtros, textvariable=self.fecha_filtro_eventos, width=12).grid(row=0, column=1, padx=5)
       
        ttk.Label(marco_filtros, text="Tipo:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.tipo_filtro_eventos = tk.StringVar(value="Todos")
        ttk.Combobox(marco_filtros, textvariable=self.tipo_filtro_eventos,
                    values=["Todos", "Alarma", "Comando", "Observación"],
                    width=12).grid(row=0, column=3, padx=5)
       
        ttk.Button(marco_filtros, text="Filtrar", command=self.filtrar_eventos).grid(row=0, column=4, padx=5)
        ttk.Button(marco_filtros, text="Limpiar", command=self.limpiar_filtros_eventos).grid(row=0, column=5, padx=5)
       
        # Lista de eventos
        marco_lista = ttk.LabelFrame(solapa, text="EVENTOS REGISTRADOS", padding=10)
        marco_lista.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        columnas = ("ID", "Fecha", "Hora", "Tipo", "Descripción")
        self.tabla_eventos = ttk.Treeview(marco_lista, columns=columnas,
                                        show="headings", height=15)
       
        anchos = [50, 80, 80, 80, 300]
        for col, ancho in zip(columnas, anchos):
            self.tabla_eventos.heading(col, text=col)
            self.tabla_eventos.column(col, width=ancho)
       
        scrollbar_v = ttk.Scrollbar(marco_lista, orient=tk.VERTICAL,
                                   command=self.tabla_eventos.yview)
        scrollbar_h = ttk.Scrollbar(marco_lista, orient=tk.HORIZONTAL,
                                   command=self.tabla_eventos.xview)
        self.tabla_eventos.configure(yscrollcommand=scrollbar_v.set,
                                  xscrollcommand=scrollbar_h.set)
       
        self.tabla_eventos.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar_v.grid(row=0, column=1, sticky=tk.NS)
        scrollbar_h.grid(row=1, column=0, sticky=tk.EW)
       
        marco_lista.grid_rowconfigure(0, weight=1)
        marco_lista.grid_columnconfigure(0, weight=1)
       
        # Acciones
        marco_acciones = ttk.Frame(solapa)
        marco_acciones.pack(fill=tk.X, padx=5, pady=5)
       
        ttk.Button(marco_acciones, text="Exportar", command=self.exportar_eventos).pack(side=tk.LEFT, padx=5)
        ttk.Button(marco_acciones, text="Eliminar", command=self.eliminar_eventos).pack(side=tk.LEFT, padx=5)
        ttk.Button(marco_acciones, text="Actualizar", command=self.actualizar_lista_eventos).pack(side=tk.LEFT, padx=5)
       
        # Estadísticas
        marco_estadisticas = ttk.LabelFrame(solapa, text="ESTADÍSTICAS", padding=10)
        marco_estadisticas.pack(fill=tk.X, padx=5, pady=5)
       
        self.etiquetas_estadisticas = {}
       
        for i, (texto, clave) in enumerate([("Alarmas:", "alarmas"),
                                          ("Comandos:", "comandos"),
                                          ("Observaciones:", "observaciones"),
                                          ("Total:", "total")]):
            frame = ttk.Frame(marco_estadisticas)
            frame.grid(row=0, column=i, padx=10, pady=5, sticky=tk.W)
           
            ttk.Label(frame, text=texto).pack(side=tk.LEFT)
           
            lbl_valor = ttk.Label(frame, text="0", font=('Arial', 10, 'bold'))
            lbl_valor.pack(side=tk.LEFT, padx=5)
           
            self.etiquetas_estadisticas[clave] = lbl_valor

    def solapa_observaciones(self):
        """Crea la solapa para registrar observaciones"""
        solapa = ttk.Frame(self.cuaderno)
        self.cuaderno.add(solapa, text="Observaciones")
       
        # Nueva observación
        marco_nueva = ttk.LabelFrame(solapa, text="NUEVA OBSERVACIÓN", padding=10)
        marco_nueva.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        self.campo_texto_observacion = scrolledtext.ScrolledText(marco_nueva,
                                                          height=10,
                                                          wrap=tk.WORD,
                                                          font=('Arial', 10))
        self.campo_texto_observacion.pack(fill=tk.BOTH, expand=True, pady=5)
       
        marco_botones = ttk.Frame(marco_nueva)
        marco_botones.pack(fill=tk.X, pady=5)
       
        ttk.Button(marco_botones, text="Guardar", command=self.guardar_observacion).pack(side=tk.LEFT, padx=5)
        ttk.Button(marco_botones, text="Limpiar", command=self.limpiar_observacion).pack(side=tk.LEFT, padx=5)
       
        # Observaciones recientes
        marco_recientes = ttk.LabelFrame(solapa, text="OBSERVACIONES RECIENTES", padding=10)
        marco_recientes.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        columnas = ("Fecha", "Hora", "Observación")
        self.tabla_observaciones = ttk.Treeview(marco_recientes, columns=columnas,
                                              show="headings", height=8)
       
        anchos = [100, 80, 400]
        for col, ancho in zip(columnas, anchos):
            self.tabla_observaciones.heading(col, text=col)
            self.tabla_observaciones.column(col, width=ancho)
       
        scrollbar = ttk.Scrollbar(marco_recientes, orient=tk.VERTICAL,
                                 command=self.tabla_observaciones.yview)
        self.tabla_observaciones.configure(yscrollcommand=scrollbar.set)
       
        self.tabla_observaciones.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def barra_estado(self):
        """Crea la barra de estado en la parte inferior"""
        self.barra_estado = ttk.Frame(self.root, height=25)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)
       
        self.etiqueta_estado = ttk.Label(self.barra_estado, text="DESCONECTADO", foreground="red")
        self.etiqueta_estado.pack(side=tk.LEFT, padx=10)
       
        self.etiqueta_tiempo_com = ttk.Label(self.barra_estado, text="Com: -- s")
        self.etiqueta_tiempo_com.pack(side=tk.LEFT, padx=10)
       
        self.etiqueta_datos = ttk.Label(self.barra_estado, text="Datos: 0")
        self.etiqueta_datos.pack(side=tk.LEFT, padx=10)
       
        self.etiqueta_alarma = ttk.Label(self.barra_estado, text="ALARMA: NO", foreground="green")
        self.etiqueta_alarma.pack(side=tk.LEFT, padx=10)
       
        ttk.Separator(self.barra_estado, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
       
        self.etiqueta_hora = ttk.Label(self.barra_estado, text=datetime.now().strftime("%H:%M:%S"))
        self.etiqueta_hora.pack(side=tk.RIGHT, padx=10)
       
        self.etiqueta_fecha = ttk.Label(self.barra_estado, text=datetime.now().strftime("%Y-%m-%d"))
        self.etiqueta_fecha.pack(side=tk.RIGHT, padx=10)

    def consola(self):
        """Crea la consola de mensajes"""
        marco_consola = ttk.LabelFrame(self.root, text="CONSOLA DE MENSAJES", padding=10)
        marco_consola.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
       
        self.consola = scrolledtext.ScrolledText(marco_consola, height=8,
                                                wrap=tk.WORD, font=('Consolas', 9))
        self.consola.pack(fill=tk.BOTH, expand=True)
       
        self.consola.tag_config("ERROR", foreground="red")
        self.consola.tag_config("WARNING", foreground="orange")
        self.consola.tag_config("INFO", foreground="blue")
        self.consola.tag_config("SUCCESS", foreground="green")
        self.consola.tag_config("COMMAND", foreground="purple")
        self.consola.tag_config("DATA", foreground="black")


# FUNCIONES DE COMUNICACIÓN ____________________________________

    def buscar_puertos_disponibles(self):
        """Busca puertos COM disponibles"""
        puertos = [port.device for port in serial.tools.list_ports.comports()] # Buscas los puertos disponibles que hay conectados al disopositivo
        self.combo_puertos['values'] = puertos
        if puertos:
            self.combo_puertos.set(puertos[0])
            self.escribir_consola(f"Puertos encontrados: {', '.join(puertos)}", "INFO")
        else:
            self.escribir_consola("No se encontraron puertos COM", "WARNING")

    def conectar_serial(self):
        """Establece conexión serial con el satélite"""
        puerto = self.combo_puertos.get()
        if not puerto:
            messagebox.showerror("Error", "Seleccione un puerto COM")
            return
       
        try:
            self.puerto_serial = serial.Serial(
                port=puerto,
                baudrate=9600,
                timeout=1
            )
           
            time.sleep(2)
           
            self.recibiendo_datos = True
            self.hilo_serial = threading.Thread(target=self.recibir_datos_serial)
            self.hilo_serial.daemon = True
            self.hilo_serial.start()
           
            self.etiqueta_estado.config(text="CONECTADO", foreground="green")
            self.escribir_consola(f"Conectado a {puerto}", "SUCCESS")
            self.registrar_evento(TipoEvento.COMANDO, f"Conexión establecida en {puerto}")
           
            self.enviar_comando_serial("ESTACION:Sistema listo")
           
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar: {str(e)}")
            self.escribir_consola(f"Error de conexión: {str(e)}", "ERROR")

    def desconectar_serial(self):
        """Cierra la conexión serial"""
        self.recibiendo_datos = False
       
        if self.puerto_serial and self.puerto_serial.is_open:
            self.puerto_serial.close()
       
        self.etiqueta_estado.config(text="DESCONECTADO", foreground="red")
        self.escribir_consola("Desconectado del puerto serial", "INFO")
        self.registrar_evento(TipoEvento.COMANDO, "Conexión serial cerrada")

    def recibir_datos_serial(self):
        """Hilo para recibir datos del puerto serial"""
        buffer = ""
        while self.recibiendo_datos and self.puerto_serial and self.puerto_serial.is_open:
            try:
                if self.puerto_serial.in_waiting > 0:
                    data = self.puerto_serial.read(self.puerto_serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                   
                    while '\n' in buffer:
                        linea, buffer = buffer.split('\n', 1)
                        linea = linea.strip()
                        if linea:
                            self.procesar_linea_recibida(linea)
               
                time.sleep(0.01)
               
            except Exception as e:
                self.escribir_consola(f"Error en recepción serial: {str(e)}", "ERROR")
                time.sleep(1)

    def procesar_linea_recibida(self, linea):
        """Procesa una línea recibida del satélite"""
        self.ultima_comunicacion = time.time()
       
        self.escribir_consola(f"← {linea}", "DATA")
        self.agregar_dato_recibido(linea)
       
        if linea.startswith("0:"):
            self.procesar_mensaje_error(linea)
            return
       
        if linea.startswith("5:"):
            self.procesar_confirmacion(linea)
            return
       
        if ':' in linea and linea.count(':') >= 2:
            if self.verificar_checksum(linea):
                datos = linea.rsplit(':', 1)[0]
                self.procesar_datos_con_checksum(datos)
            else:
                self.escribir_consola(f"Checksum incorrecto: {linea}", "ERROR")
                return
       
        if linea.startswith("1:"): # Datos temp y hum con formato 1:temp:2:hum:3:mediatemp:mediahum (si media en satélite) 1:temp:2:hum (si media en tierra) (más el checksum)
            self.procesar_datos_dht(linea)
        elif linea.startswith("4:"): # Datos Radar con formato 4:angulo:5:dist (más el checksum)
            self.procesar_datos_radar(linea)
        elif linea.startswith("6:"): # Datos orbita 6:tiempoórbita (más checksum)
            self.procesar_datos_orbita(linea)
        elif linea.startswith("14:"):  # Obtener temperatura en tiempo real
            self.procesar_temperatura_actual(linea)
        elif linea.startswith("15:"): # Obtener todos los sensores
            self.procesar_todos_sensores(linea)
        elif linea.startswith("ESTACION:"):
            self.escribir_consola(linea, "INFO")

    def agregar_dato_recibido(self, linea):
        """Agrega un dato recibido a la lista en la solapa Control"""
        try:
            hora = datetime.now().strftime("%H:%M:%S")
            estado = "OK"
           
            if linea.startswith("1:"):
                partes = linea.split(':')
                if len(partes) >= 4:
                    temp = float(partes[1])
                    hum = float(partes[3])
                    self.tabla_datos_recibidos.insert("", 0, values=(hora, "DHT", f"{temp:.1f}°C", f"{hum:.1f}%", estado))
                   
            elif linea.startswith("4:"):
                partes = linea.split(':')
                if len(partes) >= 4:
                    angulo = int(partes[1])
                    distancia = int(partes[3])
                    self.tabla_datos_recibidos.insert("", 0, values=(hora, "RADAR", f"{angulo}°", f"{distancia}cm", estado))
                   
            elif linea.startswith("6:"):
                partes = linea.split(':')
                if len(partes) >= 2:
                    tiempo = float(partes[1])
                    self.tabla_datos_recibidos.insert("", 0, values=(hora, "ÓRBITA", f"{tiempo:.1f}s", "", estado))
               
            elif linea.startswith("0:"):
                error_msg = linea[2:] if len(linea) > 2 else "Error"
                self.tabla_datos_recibidos.insert("", 0, values=(hora, "ERROR", error_msg, "", "ERROR"))
               
            elif linea.startswith("5:"):
                confirmacion = linea[2:] if len(linea) > 2 else "Confirmado"
                self.tabla_datos_recibidos.insert("", 0, values=(hora, "CONFIRM", confirmacion, "", estado))
           
            # Limitar a los últimos 30 registros
            items = self.tabla_datos_recibidos.get_children()
            if len(items) > 30:
                for item in items[30:]:
                    self.tabla_datos_recibidos.delete(item)
                   
        except Exception:
            pass

    def verificar_checksum(self, mensaje):
        """Verifica el checksum de un mensaje"""
        try:
            partes = mensaje.rsplit(':', 1)
            if len(partes) != 2:
                return False
           
            datos = partes[0]
            checksum_recibido = int(partes[1])
           
            checksum_calculado = 0
            for char in datos:
                checksum_calculado += ord(char)
            checksum_calculado %= CHECKSUM_MOD
           
            return checksum_calculado == checksum_recibido
           
        except:
            return False

    def calcular_checksum(self, datos):
        """Calcula el checksum para un mensaje"""
        checksum = 0
        for char in datos:
            checksum += ord(char)
        return checksum % CHECKSUM_MOD

    def enviar_comando_serial(self, comando):
        """Envía un comando al satélite"""
        if not self.puerto_serial or not self.puerto_serial.is_open:
            self.escribir_consola("No hay conexión serial", "ERROR")
            return
       
        try:
            if ':' in comando and not comando.startswith("ESTACION:"):
                checksum = self.calcular_checksum(comando)
                comando_completo = f"{comando}:{checksum}"
            else:
                comando_completo = comando
           
            self.puerto_serial.write((comando_completo + '\n').encode())
           
            self.escribir_consola(f"→ {comando}", "COMMAND")
            self.registrar_evento(TipoEvento.COMANDO, f"Comando enviado: {comando}")
           
        except Exception as e:
            self.escribir_consola(f"Error enviando comando: {str(e)}", "ERROR")


# PROCESAMIENTO DE DATOS ____________________________________

    def procesar_datos_dht(self, datos):
        """Procesa datos del sensor DHT que le llegan"""
        try:
            partes = datos.split(':')
           
            if len(partes) >= 3:
                temp = float(partes[1])
                hum = float(partes[3])
               
                # Si había error y ahora llegan datos válidos, limpiar error
                if self.error_dht:
                    self.error_dht = False
                    self.actualizar_estado_sensor('DHT', True)
                    self.escribir_consola("Sensor DHT restablecido", "SUCCESS")
                    self.registrar_evento(TipoEvento.COMANDO, "Sensor DHT restablecido")
               
                self.ultimo_dht_valido = (temp, hum, time.time())
               
                # Actualizar métricas
                self.etiquetas_metricas["temperatura_actual"].config(text=f"{temp:.1f}")
                self.etiquetas_metricas["humedad_actual"].config(text=f"{hum:.1f}")
               
                # Actualizar mínimos y máximos
                if self.temperaturas:
                    self.etiquetas_metricas["temperatura_min"].config(text=f"{min(self.temperaturas):.1f}")
                    self.etiquetas_metricas["temperatura_max"].config(text=f"{max(self.temperaturas):.1f}")
                if self.humedades:
                    self.etiquetas_metricas["humedad_min"].config(text=f"{min(self.humedades):.1f}")
                    self.etiquetas_metricas["humedad_max"].config(text=f"{max(self.humedades):.1f}")
               
                # Agregar a buffers
                self.temperaturas.append(temp)
                self.humedades.append(hum)
                self.buffer_temp_media.append(temp)
                self.buffer_hum_media.append(hum)
                self.marcas_tiempo.append(time.time())
               
                # Calcular medias
                if len(self.buffer_temp_media) > 0:
                    media_temp = sum(self.buffer_temp_media) / len(self.buffer_temp_media)
                    self.medidas_temp_media.append(media_temp)
                    self.etiquetas_metricas["temperatura_media"].config(text=f"{media_temp:.1f}")
               
                if len(self.buffer_hum_media) > 0:
                    media_hum = sum(self.buffer_hum_media) / len(self.buffer_hum_media)
                    self.medidas_hum_media.append(media_hum)
                    self.etiquetas_metricas["humedad_media"].config(text=f"{media_hum:.1f}")
               
                # Verificar alarmas
                self.verificar_alarma_temperatura(temp)
                self.verificar_alarma_humedad(hum)
               
                # Actualizar gráficas
                self.actualizar_graficas_temperatura()
                self.actualizar_graficas_humedad()
               
        except Exception as e:
            self.escribir_consola(f"Error procesando DHT: {str(e)}", "ERROR")

    def procesar_datos_radar(self, datos):
        """Procesa los datos del radar que le llegan"""
        try:
            partes = datos.split(':')
           
            if len(partes) >= 3:
                angulo = int(partes[1])
                distancia = int(partes[3])
               
                if 0 <= angulo <= 180 and 2 <= distancia <= 400:
                    # Si había error y ahora llegan datos válidos, limpiar error
                    if self.error_radar:
                        self.error_radar = False
                        self.actualizar_estado_sensor('RADAR', True)
                        self.escribir_consola("Sensor Radar restablecido", "SUCCESS")
                        self.registrar_evento(TipoEvento.COMANDO, "Sensor Radar restablecido")
                   
                    self.ultimo_radar_valido = (angulo, distancia, time.time())
                   
                    self.etiquetas_metricas["angulo_actual"].config(text=f"{angulo}")
                    self.etiquetas_metricas["distancia_actual"].config(text=f"{distancia}")
                   
                    self.angulos_radar.append(angulo)
                    self.distancias_radar.append(distancia)
                   
                    self.actualizar_radar_polar(angulo, distancia)
                    self.actualizar_estadisticas_radar()
                   
        except Exception as e:
            self.escribir_consola(f"Error procesando radar: {str(e)}", "ERROR")

    def procesar_datos_orbita(self, datos):
        """Procesa datos de la órbita que le llegan"""
        try:
            partes = datos.split(':')
           
            if len(partes) >= 2:
                tiempo_orbita = float(partes[1])
               
                # Si había error y ahora llegan datos válidos, limpiar error
                if self.error_orbita:
                    self.error_orbita = False
                    self.actualizar_estado_sensor('ORBITA', True)
                    self.escribir_consola("Datos Órbita restablecidos", "SUCCESS")
                    self.registrar_evento(TipoEvento.COMANDO, "Datos Órbita restablecidos")
               
                # Calcular posición 3D
                angulo = (tiempo_orbita % 3600) / 3600 * 2 * math.pi
                radio = 1.5
               
                x = radio * math.cos(angulo)
                y = radio * math.sin(angulo) * math.cos(math.radians(45))
                z = radio * math.sin(angulo) * math.sin(math.radians(45))
               
                self.ultimo_orbita_valido = (x, y, z, time.time())
               
                self.tiempos_orbita.append(tiempo_orbita)
                self.posiciones_orbita.append((x, y, z))
               
                # Actualizar métricas
                self.etiquetas_orbita["tiempo_orbita"].config(text=f"{tiempo_orbita:.1f}")
                self.etiquetas_orbita["posicion_x"].config(text=f"{x:.2f}")
                self.etiquetas_orbita["posicion_y"].config(text=f"{y:.2f}")
                self.etiquetas_orbita["posicion_z"].config(text=f"{z:.2f}")
               
                # Parámetros orbitales
                altitud = 400
                velocidad = 7.66
                periodo = 92
                inclinacion = 45
               
                self.etiquetas_orbita["altitud"].config(text=f"{altitud}")
                self.etiquetas_orbita["velocidad"].config(text=f"{velocidad:.2f}")
                self.etiquetas_orbita["periodo"].config(text=f"{periodo}")
                self.etiquetas_orbita["inclinacion"].config(text=f"{inclinacion}")
                self.etiquetas_orbita["estado_orbita"].config(text="Normal")
               
                # Agregar a tabla histórica
                hora = datetime.now().strftime("%H:%M:%S")
                self.tabla_orbita.insert("", 0, values=(hora, f"{tiempo_orbita:.1f}",
                                                      f"{x:.2f}", f"{y:.2f}", f"{z:.2f}"))
               
                # Actualizar animación 3D
                if self.animacion_orbita_activa:
                    self.actualizar_animacion_orbita_3d(x, y, z)
               
        except Exception as e:
            self.escribir_consola(f"Error procesando órbita: {str(e)}", "ERROR")

    def procesar_mensaje_error(self, datos):
        """Procesa mensajes de error"""
        error_msg = datos[2:] if len(datos) > 2 else "Error desconocido"
       
        if "FalloDHT" in error_msg:
            self.error_dht = True
            self.actualizar_estado_sensor('DHT', False)
            self.escribir_consola(f"Error DHT: {error_msg}", "ERROR")
            self.registrar_evento(TipoEvento.ALARMA, f"Fallo sensor DHT: {error_msg}")
           
        elif "FalloRadar" in error_msg:
            self.error_radar = True
            self.actualizar_estado_sensor('RADAR', False)
            self.escribir_consola(f"Error Radar: {error_msg}", "ERROR")
            self.registrar_evento(TipoEvento.ALARMA, f"Fallo sensor radar: {error_msg}")
           
        elif "FalloOrbita" in error_msg:
            self.error_orbita = True
            self.actualizar_estado_sensor('ORBITA', False)
            self.escribir_consola(f"Error Órbita: {error_msg}", "ERROR")
            self.registrar_evento(TipoEvento.ALARMA, f"Fallo datos órbita: {error_msg}")
           
        else:
            self.escribir_consola(f"Error: {error_msg}", "ERROR")

    def actualizar_estado_sensor(self, sensor, estado_ok):
        """Actualiza el estado visual de un sensor"""
        if sensor == 'DHT':
            if estado_ok:
                self.etiquetas_metricas["estado_dht"].config(text="ON", foreground="green")
            else:
                self.etiquetas_metricas["estado_dht"].config(text="ERROR", foreground="red")
               
        elif sensor == 'RADAR':
            if estado_ok:
                self.etiquetas_metricas["estado_radar"].config(text="ON", foreground="green")
            else:
                self.etiquetas_metricas["estado_radar"].config(text="ERROR", foreground="red")

    def procesar_confirmacion(self, datos):
        """Procesa mensajes de confirmación"""
        confirmacion = datos[2:] if len(datos) > 2 else "Confirmación"
        self.escribir_consola(f"Confirmación: {confirmacion}", "SUCCESS")

    def procesar_temperatura_actual(self, datos):
        """Procesa temperatura actual"""
        try:
            partes = datos.split(':')
            if len(partes) >= 2:
                temp = float(partes[1])
                self.escribir_consola(f"Temperatura actual: {temp:.1f}°C", "INFO")
               
        except Exception as e:
            self.escribir_consola(f"Error procesando temperatura: {str(e)}", "ERROR")

    def procesar_todos_sensores(self, datos):
        """Procesa datos de los sensores"""
        try:
            partes = datos.split(':')
           
            if len(partes) >= 9:
                valores = {}
                i = 1
                while i < len(partes):
                    if i + 1 < len(partes):
                        valores[partes[i]] = partes[i + 1]
                    i += 2
               
                if 'TEMP' in valores:
                    temp = float(valores['TEMP'])
                    self.etiquetas_metricas["temperatura_actual"].config(text=f"{temp:.1f}")
               
                if 'HUM' in valores:
                    hum = float(valores['HUM'])
                    self.etiquetas_metricas["humedad_actual"].config(text=f"{hum:.1f}")
               
                if 'DIST' in valores:
                    dist = int(valores['DIST'])
                    self.etiquetas_metricas["distancia_actual"].config(text=f"{dist}")
               
                if 'ANG' in valores:
                    ang = int(valores['ANG'])
                    self.etiquetas_metricas["angulo_actual"].config(text=f"{ang}")
               
                self.escribir_consola("Datos de todos los sensores recibidos", "INFO")
               
        except Exception as e:
            self.escribir_consola(f"Error procesando sensores: {str(e)}", "ERROR")

    def procesar_datos_con_checksum(self, datos):
        """Procesa datos que ya han pasado la verificación de checksum"""
        pass

# CONTROL DE SENSORES __________________________

    def detener_sensor(self, sensor):
        """Detiene un sensor específico"""
        if sensor == TipoSensor.DHT:
            comando = "9:0"
            self.dht_activo.set(False)
            if not self.error_dht:
                self.etiquetas_metricas["estado_dht"].config(text="OFF", foreground="orange")
        elif sensor == TipoSensor.RADAR:
            comando = "10:0"
            self.radar_activo.set(False)
            if not self.error_radar:
                self.etiquetas_metricas["estado_radar"].config(text="OFF", foreground="orange")
        elif sensor == TipoSensor.ORBITA:
            comando = "11:0"
            self.orbita_activa.set(False)
       
        self.enviar_comando_serial(comando)
        self.escribir_consola(f"Sensor {sensor.value} detenido", "INFO")

    def reanudar_sensor(self, sensor):
        """Reanuda un sensor específico"""
        if sensor == TipoSensor.DHT:
            comando = "9:1"
            self.dht_activo.set(True)
            if not self.error_dht:
                self.etiquetas_metricas["estado_dht"].config(text="ON", foreground="green")
        elif sensor == TipoSensor.RADAR:
            comando = "10:1"
            self.radar_activo.set(True)
            if not self.error_radar:
                self.etiquetas_metricas["estado_radar"].config(text="ON", foreground="green")
        elif sensor == TipoSensor.ORBITA:
            comando = "11:1"
            self.orbita_activa.set(True)
       
        self.enviar_comando_serial(comando)
        self.escribir_consola(f"Sensor {sensor.value} reanudado", "INFO")

    def cambiar_intervalo_sensor(self, sensor):
        """Cambia el intervalo de envío de datos"""
        if sensor == TipoSensor.DHT:
            intervalo = self.intervalo_dht_ms.get()
            comando = f"1:{intervalo // 1000}"
        elif sensor == TipoSensor.RADAR:
            intervalo = self.intervalo_radar_ms.get()
            comando = f"3:{intervalo}"
        elif sensor == TipoSensor.ORBITA:
            intervalo = self.intervalo_orbita_ms.get()
            comando = f"12:{intervalo // 1000}"
       
        self.enviar_comando_serial(comando)
        self.escribir_consola(f"Intervalo {sensor.value} cambiado a {intervalo}ms", "INFO")

    def cambiar_modo_calculo_media(self):
        """Cambia el lugar donde se calcula la media"""
        calcular_en_satelite = self.calculo_media_en_satelite.get()
        comando = "6:1" if calcular_en_satelite else "6:0"
        self.enviar_comando_serial(comando)
        self.escribir_consola(f"Cálculo de medias: {'Satélite' if calcular_en_satelite else 'Tierra'}", "INFO")

    def aplicar_limite_alarma(self, tipo):
        """Aplica el límite para la alarma"""
        if tipo == 'temperatura':
            limite = self.limite_temperatura_max.get()
            comando = f"8:{limite}"
            self.escribir_consola(f"Límite de temperatura: {limite}°C", "INFO")
            self.actualizar_limite_graficas_temp()
        elif tipo == 'humedad':
            limite = self.limite_humedad_max.get()
            comando = f"17:{limite}"
            self.escribir_consola(f"Límite de humedad: {limite}%", "INFO")
            self.actualizar_limite_graficas_hum()
       
        self.enviar_comando_serial(comando)

    def cambiar_modo_radar(self):
        """Cambia el modo del radar"""
        modo_rastreo = self.modo_radar_rastreo.get()
        comando = "7:1" if modo_rastreo else "7:0"
        self.enviar_comando_serial(comando)
        self.escribir_consola(f"Modo radar: {'Rastreo' if modo_rastreo else 'Fijo'}", "INFO")

    def establecer_angulo_radar_fijo(self):
        """Establece un ángulo fijo para el radar"""
        try:
            angulo = int(self.entrada_angulo_fijo.get())
            if 0 <= angulo <= 180:
                comando = f"2:{angulo}"
                self.enviar_comando_serial(comando)
                self.escribir_consola(f"Ángulo fijo: {angulo}°", "INFO")
            else:
                messagebox.showerror("Error", "El ángulo debe estar entre 0 y 180")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")

    def detener_todos_sensores(self):
        """Detiene todos los sensores"""
        self.enviar_comando_serial("16:0")
        self.escribir_consola("Todos los sensores detenidos", "WARNING")

    def reanudar_todos_sensores(self):
        """Reanuda todos los sensores"""
        self.enviar_comando_serial("16:1")
        self.escribir_consola("Todos los sensores reanudados", "SUCCESS")

   
# ALARMAS ___________________________________________________

    def verificar_alarma_temperatura(self, temperatura):
        """Verifica si se activa la alarma de temperatura"""
        limite = self.limite_temperatura_max.get()
       
        if len(self.buffer_temp_media) >= 10:
            media = sum(self.buffer_temp_media) / len(self.buffer_temp_media)
           
            if media > limite:
                self.contador_temp_supera_limite += 1
                self.etiqueta_contador_alarma_temp.config(text=str(self.contador_temp_supera_limite))
               
                if self.contador_temp_supera_limite >= 3 and not self.alarma_temp_activada:
                    self.activar_alarma_temperatura(media, limite)
                    self.alarma_temp_activada = True
            else:
                if self.contador_temp_supera_limite > 0:
                    self.contador_temp_supera_limite = 0
                    self.alarma_temp_activada = False
                    self.etiqueta_contador_alarma_temp.config(text="0")
                    self.etiqueta_estado_alarma_temp.config(text="NORMAL", foreground="green")
       
        self.etiqueta_contador_alarma_temp.config(text=str(self.contador_temp_supera_limite))

    def verificar_alarma_humedad(self, humedad):
        """Verifica si se activa la alarma de humedad"""
        limite = self.limite_humedad_max.get()
       
        if len(self.buffer_hum_media) >= 10:
            media = sum(self.buffer_hum_media) / len(self.buffer_hum_media)
           
            if media > limite:
                self.contador_hum_supera_limite += 1
                self.etiqueta_contador_alarma_hum.config(text=str(self.contador_hum_supera_limite))
               
                if self.contador_hum_supera_limite >= 3 and not self.alarma_hum_activada:
                    self.activar_alarma_humedad(media, limite)
                    self.alarma_hum_activada = True
            else:
                if self.contador_hum_supera_limite > 0:
                    self.contador_hum_supera_limite = 0
                    self.alarma_hum_activada = False
                    self.etiqueta_contador_alarma_hum.config(text="0")
                    self.etiqueta_estado_alarma_hum.config(text="NORMAL", foreground="green")
       
        self.etiqueta_contador_alarma_hum.config(text=str(self.contador_hum_supera_limite))

    def activar_alarma_temperatura(self, valor, limite):
        """Activa la alarma de temperatura"""
        self.alarma_activada.set(True)
        self.etiqueta_alarma.config(text="ALARMA: SI", foreground="red")
        self.etiqueta_estado_alarma_temp.config(text="¡ALARMA!", foreground="red")
       
        mensaje = f"¡ALARMA! Temperatura media {valor:.1f}°C supera límite {limite}°C 3 veces"
        self.escribir_consola(mensaje, "ERROR")
        self.registrar_evento(TipoEvento.ALARMA, mensaje)
       
        self.mostrar_ventana_alarma("TEMPERATURA", valor, limite, "°C")
       
        self.root.bell()
        self.parpadear_alarma()

    def activar_alarma_humedad(self, valor, limite):
        """Activa la alarma de humedad"""
        self.alarma_activada.set(True)
        self.etiqueta_alarma.config(text="ALARMA: SI", foreground="red")
        self.etiqueta_estado_alarma_hum.config(text="¡ALARMA!", foreground="red")
       
        mensaje = f"¡ALARMA! Humedad media {valor:.1f}% supera límite {limite}% 3 veces"
        self.escribir_consola(mensaje, "ERROR")
        self.registrar_evento(TipoEvento.ALARMA, mensaje)
       
        self.mostrar_ventana_alarma("HUMEDAD", valor, limite, "%")
       
        self.root.bell()
        self.parpadear_alarma()

    def mostrar_ventana_alarma(self, tipo, valor, limite, unidad):
        """Muestra una ventana emergente de alarma"""
        ventana = tk.Toplevel(self.root)
        ventana.title("¡ALARMA ACTIVADA!")
        ventana.geometry("400x250")
        ventana.configure(bg='red')
        ventana.attributes('-topmost', True)
       
        ventana.update_idletasks()
        width = ventana.winfo_width()
        height = ventana.winfo_height()
        x = (ventana.winfo_screenwidth() // 2) - (width // 2)
        y = (ventana.winfo_screenheight() // 2) - (height // 2)
        ventana.geometry(f'{width}x{height}+{x}+{y}')
       
        tk.Label(ventana, text="¡ALARMA!", font=('Arial', 24, 'bold'),
                bg='red', fg='white').pack(pady=10)
       
        tk.Label(ventana, text="⚠️", font=('Arial', 36),
                bg='red', fg='yellow').pack()
       
        mensaje = f"{tipo}\n\n"
        mensaje += f"Valor: {valor:.1f}{unidad}\n"
        mensaje += f"Límite: {limite}{unidad}\n\n"
        mensaje += "¡Superado 3 veces consecutivas!"
       
        tk.Label(ventana, text=mensaje, font=('Arial', 12, 'bold'),
                bg='red', fg='white', justify=tk.CENTER).pack(pady=10)
       
        tk.Button(ventana, text="ACEPTAR", font=('Arial', 12, 'bold'),
                 bg='white', fg='red', command=ventana.destroy,
                 width=15, height=2).pack(pady=10)
       
        for _ in range(3):
            ventana.bell()

    def parpadear_alarma(self):
        """Hace parpadear la barra de estado cuando hay alarma"""
        if self.alarma_activada.get():
            color = "red" if self.etiqueta_alarma.cget("foreground") == "green" else "green"
            self.etiqueta_alarma.config(foreground=color)
            self.root.after(500, self.parpadear_alarma)

# ACTUALIZACIÓN DE GRÁFICAS _______________________________

    def actualizar_graficas_temperatura(self):
        """Actualiza las gráficas de temperatura"""
        if len(self.temperaturas) > 0 and len(self.marcas_tiempo) > 0:
            tiempos = [t - self.marcas_tiempo[0] for t in self.marcas_tiempo]
           
            # Asegurar que los tiempos y temperaturas tengan la misma longitud
            min_len = min(len(tiempos), len(self.temperaturas))
            tiempos = tiempos[-min_len:]
            temps = list(self.temperaturas)[-min_len:]
           
            # Gráfica tiempo real
            self.linea_temp_real.set_data(tiempos, temps)
            self.eje_temp_real.relim()
            self.eje_temp_real.autoscale_view()
           
            # Solo mostrar línea de límite si hay datos
            if tiempos:
                y_lim = self.eje_temp_real.get_ylim()
                limite = self.limite_temperatura_max.get()
               
                # Ajustar límites del eje Y para que el límite sea visible
                if limite < y_lim[0] or limite > y_lim[1]:
                    nuevo_ylim = (min(y_lim[0], limite - 5), max(y_lim[1], limite + 5))
                    self.eje_temp_real.set_ylim(nuevo_ylim)
               
                self.linea_limite_temp.set_data([tiempos[0], tiempos[-1]], [limite, limite])
           
            self.canvas_temp_real.draw()
           
            # Gráfica de medias
            if len(self.medidas_temp_media) > 0:
                tiempos_media = tiempos[-len(self.medidas_temp_media):] if len(tiempos) >= len(self.medidas_temp_media) else tiempos
                medias = list(self.medidas_temp_media)
               
                if len(tiempos_media) == len(medias):
                    self.linea_temp_media.set_data(tiempos_media, medias)
                    self.eje_temp_media.relim()
                    self.eje_temp_media.autoscale_view()
                   
                    if tiempos_media:
                        self.linea_limite_temp_media.set_data([tiempos_media[0], tiempos_media[-1]],
                                                             [self.limite_temperatura_max.get(),
                                                              self.limite_temperatura_max.get()])
                   
                    self.canvas_temp_media.draw()

    def actualizar_graficas_humedad(self):
        """Actualiza las gráficas de humedad"""
        if len(self.humedades) > 0 and len(self.marcas_tiempo) > 0:
            tiempos = [t - self.marcas_tiempo[0] for t in self.marcas_tiempo]
           
            # Asegurar que los tiempos y humedades tengan la misma longitud
            min_len = min(len(tiempos), len(self.humedades))
            tiempos = tiempos[-min_len:]
            hums = list(self.humedades)[-min_len:]
           
            # Gráfica tiempo real
            self.linea_hum_real.set_data(tiempos, hums)
            self.eje_hum_real.relim()
            self.eje_hum_real.autoscale_view()
           
            # Solo mostrar línea de límite si hay datos
            if tiempos:
                y_lim = self.eje_hum_real.get_ylim()
                limite = self.limite_humedad_max.get()
               
                # Ajustar límites del eje Y para que el límite sea visible
                if limite < y_lim[0] or limite > y_lim[1]:
                    nuevo_ylim = (min(y_lim[0], limite - 10), max(y_lim[1], limite + 10))
                    self.eje_hum_real.set_ylim(nuevo_ylim)
               
                self.linea_limite_hum.set_data([tiempos[0], tiempos[-1]], [limite, limite])
           
            self.canvas_hum_real.draw()
           
            # Gráfica de medias
            if len(self.medidas_hum_media) > 0:
                tiempos_media = tiempos[-len(self.medidas_hum_media):] if len(tiempos) >= len(self.medidas_hum_media) else tiempos
                medias = list(self.medidas_hum_media)
               
                if len(tiempos_media) == len(medias):
                    self.linea_hum_media.set_data(tiempos_media, medias)
                    self.eje_hum_media.relim()
                    self.eje_hum_media.autoscale_view()
                   
                    if tiempos_media:
                        self.linea_limite_hum_media.set_data([tiempos_media[0], tiempos_media[-1]],
                                                            [self.limite_humedad_max.get(),
                                                             self.limite_humedad_max.get()])
                   
                    self.canvas_hum_media.draw()

    def actualizar_limite_graficas_temp(self):
        """Actualiza la línea de límite en las gráficas de temperatura"""
        limite = self.limite_temperatura_max.get()
       
        if len(self.marcas_tiempo) > 0:
            tiempos = [t - self.marcas_tiempo[0] for t in self.marcas_tiempo]
           
            if tiempos:
                self.linea_limite_temp.set_data([tiempos[0], tiempos[-1]], [limite, limite])
                self.canvas_temp_real.draw()
           
            if len(self.medidas_temp_media) > 0:
                tiempos_media = tiempos[-len(self.medidas_temp_media):] if len(tiempos) >= len(self.medidas_temp_media) else tiempos
                if tiempos_media:
                    self.linea_limite_temp_media.set_data([tiempos_media[0], tiempos_media[-1]],
                                                         [limite, limite])
                    self.canvas_temp_media.draw()

    def actualizar_limite_graficas_hum(self):
        """Actualiza la línea de límite en las gráficas de humedad"""
        limite = self.limite_humedad_max.get()
       
        if len(self.marcas_tiempo) > 0:
            tiempos = [t - self.marcas_tiempo[0] for t in self.marcas_tiempo]
           
            if tiempos:
                self.linea_limite_hum.set_data([tiempos[0], tiempos[-1]], [limite, limite])
                self.canvas_hum_real.draw()
           
            if len(self.medidas_hum_media) > 0:
                tiempos_media = tiempos[-len(self.medidas_hum_media):] if len(tiempos) >= len(self.medidas_hum_media) else tiempos
                if tiempos_media:
                    self.linea_limite_hum_media.set_data([tiempos_media[0], tiempos_media[-1]],
                                                        [limite, limite])
                    self.canvas_hum_media.draw()

    def actualizar_radar_polar(self, angulo=None, distancia=None):
        """Actualiza la visualización del radar polar"""
        if angulo is not None and distancia is not None:
            angulo_rad = math.radians(angulo)
           
            # Actualizar línea de medición actual
            self.linea_radar_polar.set_data([0, angulo_rad], [0, distancia])
           
            # Agregar punto actual
            self.puntos_radar.append({
                'angulo': angulo_rad,
                'distancia': distancia,
                'tiempo': time.time()
            })
           
            # Mantener solo los últimos 30 puntos
            if len(self.puntos_radar) > 30:
                self.puntos_radar = self.puntos_radar[-30:]
       
        # Actualizar scatter plot
        if self.puntos_radar:
            angulos = [p['angulo'] for p in self.puntos_radar]
            distancias = [p['distancia'] for p in self.puntos_radar]
           
            # Actualizar scatter con colores según distancia
            self.dispersor_radar_polar.set_offsets(np.column_stack([angulos, distancias]))
            self.dispersor_radar_polar.set_sizes([20] * len(self.puntos_radar))
            self.dispersor_radar_polar.set_array(np.array(distancias))
            self.dispersor_radar_polar.set_cmap('Reds')
            self.dispersor_radar_polar.set_clim(0, 400)
       
        self.canvas_radar_polar.draw()

    def actualizar_estadisticas_radar(self):
        """Actualiza las estadísticas del radar"""
        if self.distancias_radar:
            distancia_actual = self.distancias_radar[-1] if self.distancias_radar else 0
            angulo_actual = self.angulos_radar[-1] if self.angulos_radar else 0
           
            self.etiquetas_radar["angulo_radar"].config(text=f"{angulo_actual}")
            self.etiquetas_radar["distancia_radar"].config(text=f"{distancia_actual}")
           
            if self.angulos_radar and self.distancias_radar:
                min_len = min(len(self.angulos_radar), len(self.distancias_radar))
                pares = set(zip(list(self.angulos_radar)[-min_len:], list(self.distancias_radar)[-min_len:]))
                self.etiquetas_radar["objetos_detectados"].config(text=f"{len(pares)}")
            else:
                self.etiquetas_radar["objetos_detectados"].config(text="0")
           
            self.etiquetas_radar["distancia_minima"].config(
                text=f"{min(self.distancias_radar) if self.distancias_radar else 0}"
            )
            self.etiquetas_radar["distancia_maxima"].config(
                text=f"{max(self.distancias_radar) if self.distancias_radar else 0}"
            )
            self.etiquetas_radar["distancia_media"].config(
                text=f"{np.mean(list(self.distancias_radar)[-10:]) if len(self.distancias_radar) >= 10 else 0:.1f}"
            )

    def actualizar_animacion_orbita_3d(self, x, y, z):
        """Actualiza la animación de la órbita 3D"""
        if self.animacion_orbita_activa:
            self.satelite_3d.set_data([x], [y])
            self.satelite_3d.set_3d_properties([z])
           
            if len(self.posiciones_orbita) > 1:
                pos_x = [p[0] for p in self.posiciones_orbita]
                pos_y = [p[1] for p in self.posiciones_orbita]
                pos_z = [p[2] for p in self.posiciones_orbita]
                self.linea_trayectoria_3d.set_data(pos_x, pos_y)
                self.linea_trayectoria_3d.set_3d_properties(pos_z)
           
            self.canvas_orbita_3d.draw()

    def iniciar_animacion_orbita(self):
        """Inicia la animación de la órbita"""
        self.animacion_orbita_activa = True
        self.escribir_consola("Animación de órbita iniciada", "INFO")

    def detener_animacion_orbita(self):
        """Detiene la animación de la órbita"""
        self.animacion_orbita_activa = False
        self.escribir_consola("Animación de órbita detenida", "INFO")


# EVENTOS ______________________________________

    def registrar_evento(self, tipo, descripcion):
        """Registra un evento en el sistema"""
        evento = {
            'id': len(self.eventos_registrados) + 1,
            'fecha': datetime.now().strftime("%Y-%m-%d"),
            'hora': datetime.now().strftime("%H:%M:%S"),
            'tipo': tipo.value,
            'descripcion': descripcion
        }
       
        self.eventos_registrados.append(evento)
        self.guardar_evento_archivo(evento)
       
        if self.cuaderno.index(self.cuaderno.select()) == 4:
            self.actualizar_lista_eventos()
       
        self.actualizar_estadisticas_eventos()

    def guardar_evento_archivo(self, evento):
        """Guarda un evento en el archivo correspondiente"""
        nombre_archivo = f"logs/{evento['tipo']}_{evento['fecha']}.log"
       
        with open(nombre_archivo, 'a', encoding='utf-8') as f:
            f.write(f"{evento['fecha']} {evento['hora']} - {evento['descripcion']}\n")

    def filtrar_eventos(self):
        """Filtra los eventos según los criterios seleccionados"""
        fecha_filtro = self.fecha_filtro_eventos.get()
        tipo_filtro = self.tipo_filtro_eventos.get()
       
        for item in self.tabla_eventos.get_children():
            self.tabla_eventos.delete(item)
       
        self.eventos_filtrados = []
        for evento in self.eventos_registrados:
            if fecha_filtro and evento['fecha'] != fecha_filtro:
                continue
           
            if tipo_filtro != "Todos" and evento['tipo'] != tipo_filtro.lower():
                continue
           
            self.eventos_filtrados.append(evento)
           
            self.tabla_eventos.insert("", "end", values=(
                evento['id'],
                evento['fecha'],
                evento['hora'],
                evento['tipo'].upper(),
                evento['descripcion']
            ))

    def limpiar_filtros_eventos(self):
        """Limpia los filtros de eventos"""
        self.fecha_filtro_eventos.set(datetime.now().strftime("%Y-%m-%d"))
        self.tipo_filtro_eventos.set("Todos")
        self.filtrar_eventos()

    def actualizar_lista_eventos(self):
        """Actualiza la lista de eventos"""
        self.filtrar_eventos()

    def exportar_eventos(self):
        """Exporta los eventos a un archivo JSON"""
        try:
            archivo = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Guardar eventos como"
            )
           
            if archivo:
                with open(archivo, 'w', encoding='utf-8') as f:
                    json.dump(self.eventos_filtrados, f, indent=2, ensure_ascii=False)
               
                self.escribir_consola(f"Eventos exportados a {archivo}", "SUCCESS")
                messagebox.showinfo("Éxito", f"Eventos exportados a:\n{archivo}")
               
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")

    def eliminar_eventos(self):
        """Elimina los eventos seleccionados"""
        seleccionados = self.tabla_eventos.selection()
        if not seleccionados:
            return
       
        if messagebox.askyesno("Confirmar", f"¿Eliminar {len(seleccionados)} evento(s)?"):
            for item in seleccionados:
                evento_id = int(self.tabla_eventos.item(item, 'values')[0])
                self.eventos_registrados = [e for e in self.eventos_registrados if e['id'] != evento_id]
           
            for i, evento in enumerate(self.eventos_registrados, 1):
                evento['id'] = i
           
            self.actualizar_lista_eventos()
            self.actualizar_estadisticas_eventos()
           
            self.escribir_consola(f"{len(seleccionados)} evento(s) eliminado(s)", "INFO")

    def actualizar_estadisticas_eventos(self):
        """Actualiza las estadísticas de eventos"""
        contadores = {
            'alarma': 0,
            'comando': 0,
            'observacion': 0,
            'total': len(self.eventos_registrados)
        }
       
        for evento in self.eventos_registrados:
            if evento['tipo'] == 'alarma':
                contadores['alarma'] += 1
            elif evento['tipo'] == 'comando':
                contadores['comando'] += 1
            elif evento['tipo'] == 'observacion':
                contadores['observacion'] += 1
       
        self.etiquetas_estadisticas['alarmas'].config(text=str(contadores['alarma']))
        self.etiquetas_estadisticas['comandos'].config(text=str(contadores['comando']))
        self.etiquetas_estadisticas['observaciones'].config(text=str(contadores['observacion']))
        self.etiquetas_estadisticas['total'].config(text=str(contadores['total']))


# OBSERVACIONES ____________________________________________

    def guardar_observacion(self):
        """Guarda una observación del usuario"""
        observacion = self.campo_texto_observacion.get("1.0", tk.END).strip()
       
        if observacion:
            self.registrar_evento(TipoEvento.OBSERVACION, observacion)
           
            hora_actual = datetime.now().strftime("%H:%M:%S")
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            self.tabla_observaciones.insert("", 0, values=(fecha_actual, hora_actual, observacion))
           
            self.campo_texto_observacion.delete("1.0", tk.END)
           
            self.escribir_consola("Observación guardada", "SUCCESS")
            messagebox.showinfo("Éxito", "Observación guardada correctamente")
        else:
            messagebox.showwarning("Advertencia", "La observación no puede estar vacía")

    def limpiar_observacion(self):
        """Limpia el área de texto de observaciones"""
        self.campo_texto_observacion.delete("1.0", tk.END)


# EXPORTACIÓN DE DATOS____________________________________________

    def exportar_datos_radar(self):
        """Exporta los datos del radar a CSV"""
        try:
            archivo = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Guardar datos radar como"
            )
           
            if archivo:
                # Crear datos a partir de las listas actuales
                datos = []
                timestamp_base = time.time() - len(self.angulos_radar) if self.angulos_radar else time.time()
               
                for i in range(min(len(self.angulos_radar), len(self.distancias_radar))):
                    datos.append({
                        'Tiempo': f"{i}s",
                        'Ángulo (°)': self.angulos_radar[i],
                        'Distancia (cm)': self.distancias_radar[i]
                    })
               
                if datos:
                    with open(archivo, 'w', newline='', encoding='utf-8') as f:
                        campos = ['Tiempo', 'Ángulo (°)', 'Distancia (cm)']
                        escritor = csv.DictWriter(f, fieldnames=campos)
                       
                        escritor.writeheader()
                        for fila in datos:
                            escritor.writerow(fila)
                   
                    self.escribir_consola(f"Datos radar exportados a {archivo}", "SUCCESS")
                    messagebox.showinfo("Éxito", f"Datos exportados a:\n{archivo}")
                else:
                    messagebox.showwarning("Sin datos", "No hay datos para exportar")
                   
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")

    def limpiar_historial_radar(self):
        """Limpia el historial del radar"""
        self.angulos_radar.clear()
        self.distancias_radar.clear()
        self.puntos_radar.clear()
        self.actualizar_radar_polar()
        self.escribir_consola("Historial radar limpiado", "INFO")

# MENSAJES _______________________________

    def escribir_consola(self, mensaje, tipo="INFO"):
        """Escribe un mensaje en la consola"""
        self.consola.config(state=tk.NORMAL)
       
        hora = datetime.now().strftime("%H:%M:%S")
        mensaje_completo = f"[{hora}] {mensaje}\n"
       
        self.consola.insert(tk.END, mensaje_completo, tipo)
        self.consola.see(tk.END)
        self.consola.config(state=tk.DISABLED)

# ACTUALIZACIONES ________________________________

    def actualizaciones_periodicas(self):
        """Inicia las actualizaciones periódicas del sistema"""
        self.actualizar_hora_fecha()
        self.verificar_comunicacion()
        self.verificar_sensores_inactivos()
        self.root.after(1000, self.actualizaciones_periodicas)

    def actualizar_hora_fecha(self):
        """Actualiza la hora y fecha en la barra de estado"""
        ahora = datetime.now()
        self.etiqueta_hora.config(text=ahora.strftime("%H:%M:%S"))
        self.etiqueta_fecha.config(text=ahora.strftime("%Y-%m-%d"))

    def verificar_comunicacion(self):
        """Verifica si hay comunicación con el satélite"""
        tiempo_desde_com = time.time() - self.ultima_comunicacion
       
        if tiempo_desde_com > self.tiempo_espera_comunicacion:
            self.etiqueta_tiempo_com.config(text=f"Com: {int(tiempo_desde_com)} s",
                                      foreground="red")
           
            if tiempo_desde_com > self.tiempo_espera_comunicacion * 2:
                self.etiqueta_estado.config(text="SIN COMUNICACIÓN", foreground="red")
               
                if not hasattr(self, 'tiempo_espera_loggeado') or not self.tiempo_espera_loggeado:
                    self.escribir_consola("ALERTA: Sin comunicación con el satélite", "ERROR")
                    self.registrar_evento(TipoEvento.ALARMA, "Pérdida de comunicación con el satélite")
                    self.tiempo_espera_loggeado = True
        else:
            self.etiqueta_tiempo_com.config(text=f"Com: {int(tiempo_desde_com)} s",
                                      foreground="green")
            self.tiempo_espera_loggeado = False
       
        total_datos = len(self.temperaturas) + len(self.distancias_radar) + len(self.tiempos_orbita)
        self.etiqueta_datos.config(text=f"Datos: {total_datos}")

    def verificar_sensores_inactivos(self):
        """Verifica si los sensores llevan mucho tiempo sin enviar datos"""
        tiempo_actual = time.time()
       
        # Verificar DHT
        if self.ultimo_dht_valido and (tiempo_actual - self.ultimo_dht_valido[2]) > 30:
            if not self.error_dht:
                self.escribir_consola("Advertencia: DHT inactivo por más de 30 segundos", "WARNING")
       
        # Verificar Radar
        if self.ultimo_radar_valido and (tiempo_actual - self.ultimo_radar_valido[2]) > 30:
            if not self.error_radar:
                self.escribir_consola("Advertencia: Radar inactivo por más de 30 segundos", "WARNING")
       
        # Verificar Órbita
        if self.ultimo_orbita_valido and (tiempo_actual - self.ultimo_orbita_valido[3]) > 30:
            if not self.error_orbita:
                self.escribir_consola("Advertencia: Órbita inactiva por más de 30 segundos", "WARNING")


# ======================= FUNCIÓN PRINCIPAL =======================
def main():
    """Función principal de la aplicación"""
    root = tk.Tk()
   
    app = EstacionTierraSatelite(root)
   
    def on_closing():
        "Salir de la aplicación"
        if messagebox.askokcancel("Salir", "¿Está seguro de que desea salir?"):
            app.recibiendo_datos = False
            if app.puerto_serial and app.puerto_serial.is_open:
                app.puerto_serial.close()
            root.destroy()
   
    root.protocol("WM_DELETE_WINDOW", on_closing)
   
    root.mainloop()

if __name__ == "__main__":
    main()
