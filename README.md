# 🛰️ PROJECTE Grup 15 🛰️

## 👥 Integrantes del Equipo
ASIER                              LUCIA                                MIGUEL

## Descripcion del proyecto 

*CARACTERÍSTICAS PRINCIPALES*
<div align="left">
- Sistema satélite-tierra con comunicación LoRa
  - Tecnología LoRa SX1276 a 433 MHz 
  - Validación de datos mediante checksum
- Sensores integrados en satélite
  - DHT11(sensor) para temperatura y humedad
  - HC-SR04(sensor ultrasonidos) para medición de distancia
  - Servo SG90 para orientación tipo radar
- Interfaz gráfica en tiempo real
  - Desarrollada en Python con Tkinter
  - Visualización de las graficas 
- Protocolo de comunicación estructurado
  - Múltiples tipos de mensaje (temperatura, humedad, distancia)
  - Sistema de control bidireccional
- Sistema de alarmas y validación
  - Detección de 3 medias consecutivas sobre límite en temperatura/humedad
  - Alarmas visuales y auditivas (LEDs y buzzer)
  - Checksum para comprobar los datos

</div>


# Versiones
## Version 1:

Nosaltes durant aquesta versió 1 no hem aconseguit cumplir amb tots els passos inidcats, hem aconseguit fer fins als pas 3, es a dir; hem fet que envïi les dades de temperatura, les rebi l'altre ordinador, i les posi en una gràfica que esta incrustada a una interfaç. Pensem que no hem pogut acabar tots els punts de la versió 1 ja que cap dels 3 pràcticament havia fet servir mai l'Arduino i a les primeres classes vam tenir dificultats però a mesura que hem anat pràcticant ja ens han començat a sortir les coses millor. Per ultim, pensem que hem treballat bastant be però ens ha faltat més comunicació i més coordinació entre nosaltres. Esperem fer-ho millor en les pròximes versions.

VIDEO V1:
https://drive.google.com/file/d/1L8MmuHGUYzk3Fw5PDx3Sk3lThohy9duL/view?usp=drive_link



## Version 2:

En aquest temps hem acabat el que ens faltaba per acabar de la versio 1 i hem començat la versio 2, tot i que encara ens falten bastantes coses i els codis no funcionen amb tot junt. Per aixo en el video nomes surt la versio 1 i el codi del test unitari que tenim de la versio 2 que si que funciona. 
Hem tingut algunes dificultats en ajuntar aquest codis i per aixo com no esta del tot be no hi ha video. Ens assegurarem que per a la versio 3 estara tot fet.

VIDEO V2:
https://drive.google.com/file/d/17cMnbxN7gR1Ks_FBl84Vf93BH628MKZ-/view?usp=sharing

## Version 3:
Tenim tot el que demana menys la gràfica de les òrbites ja que no acaba de surtir be a la interfaç. També com diem en el video ens falta arreglar petites coses de la interfaç i de l'alarma.

Video V2:
https://drive.google.com/file/d/1Vp3Mgnz5NVvSKLzOE6YZtBhTxNeMwWKn/view?usp=sharing


















<div align="center">

![System Architecture](https://img.shields.io/badge/Architecture-Satellite_Terrestrial-blueviolet)
![Communication](https://img.shields.io/badge/Communication-LoRa_433MHz-009688)
![Sensors](https://img.shields.io/badge/Sensors-DHT11_HC--SR04-FF9800)
![Interface](https://img.shields.io/badge/Interface-Python_Tkinter-2196F3)
![Status](https://img.shields.io/badge/Status-Completed-4CAF50)
![Version](https://img.shields.io/badge/Version-4.0-9C27B0)
![License](https://img.shields.io/badge/License-Academic-607D8B)

<br />

<img src="https://img.shields.io/badge/Arduino-UNO-00979D?style=for-the-badge&logo=arduino&logoColor=white" />
<img src="https://img.shields.io/badge/Python-3.8-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/LoRa-SX1276-00BCD4?style=for-the-badge" />
<img src="https://img.shields.io/badge/Matplotlib-3D_Visualization-11557C?style=for-the-badge&logo=matplotlib" />

<br />

**Sistema de comunicación satélite-tierra con tecnología LoRa**  

[🎥 Videos de las versiones](#-videos-de-las-versiones) · [📡 Protocolo de aplicación](#-protocolo-de-comunicación) · [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema) · [📁 Estructura del Proyecto](#-estructura-del-proyecto)

</div>

## 🎥 Videos de las versiones

<div align="center">

| Versión | Video | Estado | Funcionalidades |
|---------|-------|--------|----------------|
| **V1** | [![Version 1](https://img.shields.io/badge/Watch-FF6B6B?style=for-the-badge)](https://drive.google.com/file/d/1L8MmuHGUYzk3Fw5PDx3Sk3lThohy9duL/view) | ✅ Completado | Comunicación básica + DHT11 |
| **V2** | [![Version 2](https://img.shields.io/badge/Watch-4ECDC4?style=for-the-badge)](https://drive.google.com/file/d/17cMnbxN7gR1Ks_FBl84Vf93BH628MKZ-/view) | ✅ Completado | Sensor HC-SR04 + Radar |
| **V3** | [![Version 3](https://img.shields.io/badge/Watch-FFD166?style=for-the-badge)](https://drive.google.com/file/d/1Vp3Mgnz5NVvSKLzOE6YZtBhTxNeMwWKn/view) | ✅ Completado | LoRa + Órbita 2D |
| **V4** | [![Version Final](https://img.shields.io/badge/Watch-06D6A0?style=for-the-badge)](#) | ✅ Completado | Sistema completo + mejoras |

</div>

## 📡 Protocolo de Comunicación

```
# Formato Satélite→Tierra: 1:temp:hum|2:dist:ang|3:x:y:z|4:alarma|5:media|ORBIT|tiempo:x:y:z|6:ack

-> ack = acknowledgment (confirmación de recepción)
```


## 🏗️ Arquitectura del Sistema

```mermaid
graph LR
    subgraph "🛰️ SATÉLITE"
        A[DHT11] --> B[Arduino]
        C[HC-SR04] --> B
        D[Servo] --> B
        B --> E[LoRa TX]
    end
    
    subgraph "📡 COMUNICACIÓN"
        E -- "433MHz<br/>2km alcance" --> F
    end
    
    subgraph "🌍 TIERRA"
        F[LoRa RX] --> G[Arduino]
        G --> H[Python GUI]
        H --> I[Gráfica Temperatura/Humedad]
        H --> J[Gráfica Radar]
        H --> K[Orbita satélite 2D]
        H --> L[Observaciones]
    end
    
    style A fill:#FF6B6B,color:#fff
    style C fill:#4ECDC4,color:#fff
    style D fill:#FFD166,color:#fff
    style B fill:#6C63FF,color:#fff
    style E fill:#2D2B55,color:#fff
    
    style F fill:#2D2B55,color:#fff
    style G fill:#6C63FF,color:#fff
    style H fill:#06D6A0,color:#fff
    
    style I fill:#FF6B6B,color:#fff
    style J fill:#4ECDC4,color:#fff
    style K fill:#FFD166,color:#fff
    style L fill:#9C27B0,color:#fff
```

## 👥 Integrantes del Equipo

<div align="center">
<table>
  <tr>
    <td align="center" colspan="3">
      <h3>💻<strong>Los desarrolladores</strong>💻</h3>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong> Asier Romero</strong><br>
    </td>
    <td align="center">
      <strong> Lucía Vega</strong><br>
    </td>
    <td align="center">
      <strong> Miguel Fernández</strong><br>
    </td>
  </tr>
  <tr>
    <td align="center" colspan="3">
      <em>Grupo 15 - Sistema Satelital</em>
    </td>
  </tr>
</table>
</div>


## 📁 Estructura del Proyecto

```
🌐 SISTEMA_SATELITAL/
├── 🛰️ Codigo_Satelite/
│   ├── ⚡ satelite_final.ino
│   └── 📚 librerias/
│
├── 🌍 Codigo_Estacion_Tierra/
│   ├── ⚡ estacion_tierra_final.ino
│   └── 📚 librerias/
│
├── 🐍 Interfaz_Python/
│   ├── 🎮 interfaz_final.py
│   ├── 📊 graficas.py
│   ├── 📡 comunicacion.py
│   └── 📝 logging_sistema.py
│
├── 🧪 Tests_Unitarios/
│   ├── 🌡️ test_temperatura.ino
│   ├── 📶 test_comunicacion.ino
│   ├── 📏 test_proximidad.ino
│   └️ 🛰️ test_orbita.ino
│
├── 📚 Documentacion/
│   ├── 🔌 esquemas_circuitos.pdf
│   ├── 📡 protocolo_comunicacion.md
│   └️ 📖 manual_usuario.pdf
│
└── 🎥 Media/
    ├── 📐 diagramas/
    ├️ 📸 fotos_montaje/
    └️ 🎬 videos/
```


## 📚 Licencia

<div align="center">

**Licencia Académica**  
Este proyecto se distribuye para fines educativos.  

**© 2025 Grupo 15 - Sistema Satelital**

</div>

---

<div align="center">

**Asignatura:** Ciencias de la computación 
**Institución:** EETAC
**Año académico:** 2025  
**Última actualización:** Diciembre 2025

[⬆️ Volver al inicio](#-sistema-satelital:-grupo-15)

</div>





