# 🛰️ PROYECTO DE COMUNICACIÓN SATÉLITE-TIERRA  Grup 15 🛰️

## 👥 Integrantes del Equipo
ASIER                             LUCIA                                MIGUEL
## 👥 Integrantes del Equipo

<div style="display: flex; justify-content: center; gap: 40px; flex-wrap: wrap; margin: 25px 0;">
    <!-- Asier -->
    <div style="text-align: center;">
        <img src="https://github.com/user-attachments/assets/b92bcb36-00b6-4f34-aa8e-21554eda813d" 
             width="150" 
             height="150" 
             style="border-radius: 50%; object-fit: cover; border: 4px solid #06D6A0; box-shadow: 0 6px 12px rgba(6, 214, 160, 0.3);">
        <p style="margin-top: 10px; font-weight: bold; color: #06D6A0; font-size: 16px;">🌍 ASIER</p>
    </div>
    <div style="text-align: center;">
        <img src="https://github.com/user-attachments/assets/c3eb66b5-f151-4c50-864f-842789a05926" 
             width="150" 
             height="150" 
             style="border-radius: 50%; object-fit: cover; border: 4px solid #6C63FF; box-shadow: 0 6px 12px rgba(108, 99, 255, 0.3);">
        <p style="margin-top: 10px; font-weight: bold; color: #6C63FF; font-size: 16px;">🛰️ LUCÍA</p>
    </div>
    
</div>



El proyecto consiste en un sistema de comunicación bidireccional entre un satélite simulado y una estación terrestre, implementado con dos módulos Arduino. El satélite captura datos mediante sensores y los transmite a la estación terrestre, donde una interfaz gráfica en Python visualiza la información en tiempo real.

**CARACTERÍSTICAS PRINCIPALES**

<div align="left">
  
- Sistema satélite-tierra con comunicación LoRa
  - Tecnología LoRa SX1276 a 433 MHz 
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
  - Alarmas visuales y auditivas (LEDs y buzzer)
  

</div>

**Estructura del Proyecto**

```mermaid
graph TB
    subgraph "🛰️ SATÉLITE"
        A[DHT11 - Temperatura/Humedad] --> B[Arduino Satélite]
        C[HC-SR04 - Distancia] --> B
        D[Servo SG90 - Orientación] --> B
        B --> E[Transmisor LoRa]
    end
    
    subgraph "📡 COMUNICACIÓN"
        E -- "433 MHz · Protocolo estructurado" --> F[Receptor LoRa]
    end
    
    subgraph "🌍 ESTACIÓN TERRESTRE"
        F --> G[Arduino Tierra]
        G --> H[Interfaz Python]
        
        H --> I[📊 Gráficas Tiempo Real]
        H --> J[🔄 Control Satelital]
        H --> K[🚨 Sistema de Alertas]
        
        I --> L[🌡️ Temperatura/Humedad]
        I --> M[📍 Radar de Distancia]
        I --> N[🛸 Órbita Satelital 2D]
    end
    
    style A fill:#FF6B6B,color:#fff
    style C fill:#4ECDC4,color:#fff
    style D fill:#FFD166,color:#fff
    style B fill:#6C63FF,color:#fff
    style E fill:#2D2B55,color:#fff
    style F fill:#2D2B55,color:#fff
    style G fill:#2D2B55,color:#fff
    style H fill:#6C63FF,color:#fff
    style L fill:#06D6A0,color:#fff
    style M fill:#FF6B6B,color:#fff
    style N fill:#4ECDC4,color:#fff
```


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

VIDEO V3:
https://drive.google.com/file/d/1Vp3Mgnz5NVvSKLzOE6YZtBhTxNeMwWKn/view?usp=sharing

## Version 4:

Nosaltres no hem pogut fer gaire cosa per aquesta ultima versió ja que hem estat quasi fins l'ultim dia hem estat arreglant petits errors de les versions anteriors que teniem i que han anat apareixen a mesura que anavem implementant mes coses. Per tant, nomes hem pogut fer una interfaç millorada, amb moltes opcions, mes botons i més visual, on hem agegit les mitjanes de la humitat. 

VIDEO V4:


Licencia
Este proyecto se desarrolla con fines educativos. Todos los derechos reservados al Grupo 15.

Proyecto académico · Ciéncias Computacionales
















