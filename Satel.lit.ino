#include <DHT.h>
#include <SoftwareSerial.h>
#include <Servo.h>
#include <stdint.h>

// CONFIGURACIÓN INICIAL
#define DHTPIN 2                  // Pin del sensor DHT11
#define DHTTYPE DHT11               
DHT dht(DHTPIN, DHTTYPE);          

SoftwareSerial mySerial(10, 11);    // Comunicación serial: RX=pin10, TX=pin11

// CONFIGURACIÓN RADAR
#define TRIGGER 4                 // Pin TRIGGER del ultrasónico
#define ECHO 5                    // Pin ECHO del ultrasónico
#define SERVO 6                   // Pin del servo motor

// VARIABLES RADAR
Servo servoMotor;                   
int anguloActual = 0;               
int pasoBarrido = 2;             // Incremento de ángulo por movimiento
unsigned long ultimoMovimientoRadar = 0;         // Último momento que se movió el servo
unsigned long ultimoEnvioRadar = 0;              // Último envío de datos del radar
unsigned long intervaloMovimientoRadar = 1000;   // Cada cuánto mover el servo (ms)
unsigned long intervaloEnvioRadar = 2000;       // Cada cuánto enviar datos radar (ms)
bool modoRastreoActivado = true; // true=barrido, false=ángulo fijo
int anguloFijo = 90;   

// CONSTANTES PARA SIMULACIÓN DE ÓRBITA
const double CONSTANTE_GRAVITACIONAL = 6.67430e-11;      
const double MASA_TIERRA = 5.97219e24;                   // kg
const double RADIO_TIERRA = 6371000;                     // m
const double ALTURA_SATELITE = 400000;                   // m
const double VELOCIDAD_ROTACION_TIERRA = 7.2921159e-5;   // rad/s
unsigned long INTERVALO_ACTUALIZACION_ORBITA = 1000;     // ms
const double COMPRESION_TIEMPO = 90.0;                   

// VARIABLES PARA SIMULACIÓN DE ÓRBITA
unsigned long proximaActualizacionOrbita;                
double periodoOrbitalReal;                               
double radioOrbital;                                                                      

// VARIABLES DE CONTROL DE ENVÍO DE DATOS
bool enviarDatosDHT = 1;                                 
bool enviarDatosRadar = true;                            
bool enviarDatosOrbita = true;                           
unsigned long ultimoEnvioDHT = 0;                        
unsigned long intervaloEnvioDHT = 2000UL;                // Intervalo entre envíos DHT (ms)

// BUFFER PARA TEMPERATURAS (CÁLCULO DE MEDIA)
float bufferTemperaturas[10];                         // Almacena últimas 10 temperaturas
int indiceBufferTemperatura = 0;                         
bool bufferTemperaturaLleno = false;                  // Indica si buffer está lleno
float temperaturaMediaActual = 0.0;                      

// BUFFER PARA HUMEDAD (CÁLCULO DE MEDIA)
float bufferHumedades[10];                            // Almacena últimas 10 humedadesE
int indiceBufferHumedad = 0;                            
bool bufferHumedadLleno = false;                      // Indica si buffer está lleno
float humedadMediaActual = 0.0;                       

// CONFIGURACIÓN DE CÁLCULO DE MEDIAS
bool calcularMediasEnSatelite = true;                    // true=satélite calcula, false=estación

// CONTROL DE TIMEOUT DE COMUNICACIÓN
unsigned long ultimoComandoRecibido = 0;                 // Momento del último comando
const unsigned long TIMEOUT_COMUNICACION = 10000;        // Tiempo máximo sin comunicación (ms)

// ESTADO DE INICIALIZACIÓN
bool sistemaTemperaturaIniciado = false;                 // Indica si el sistema DHT está listo


void enviarSimple(String mensaje) {  
  // Envia mensaje por serial

  mySerial.println(mensaje);
  Serial.println("Enviando simple: " + mensaje);
}

int calcularChecksum(String mensaje) {
  // Calcula el checksum de un mensaje (valor checksum 0-255)
  int checksum = 0;
  
  // Sumar valores ASCII de cada caracter
  for (unsigned int i = 0; i < mensaje.length(); i++) {
    checksum += (int)mensaje[i];
  }
  
  // Limitar a 1 byte (0-255)
  return checksum % 256;
}

void enviarConChecksum(String mensaje) {
  // Envia mensaje con checksum incluido
  int checksum = calcularChecksum(mensaje);
  String mensajeCompleto = mensaje + ":" + String(checksum);
  mySerial.println(mensajeCompleto);
  
  // Mostrar en monitor serie para depuración
  Serial.println(mensajeCompleto);
}

void simularOrbita(unsigned long tiempoActualMillis, int usarCoordenadasECEF) {
  // Simula órbita del satelite y envia datos
  //0=coordenadas inerciales, 1=coordenadas ECEF

    static unsigned long ultimoEnvioOrbita = 0;
    
    // Solo enviar si está activado y ha pasado el intervalo
    if (!enviarDatosOrbita || (tiempoActualMillis - ultimoEnvioOrbita < INTERVALO_ACTUALIZACION_ORBITA)) {
        return;
    }
    
    ultimoEnvioOrbita = tiempoActualMillis;
    
    // Convertir tiempo simulado (con compresión)
    double tiempoSegundos = (tiempoActualMillis / 1000.0) * COMPRESION_TIEMPO;
    double anguloOrbital = 2 * PI * (fmod(tiempoSegundos, periodoOrbitalReal) / periodoOrbitalReal);
    
    // Calcular posición en órbita circular (simplificado)
    double posX = radioOrbital * cos(anguloOrbital);
    double posY = radioOrbital * sin(anguloOrbital) * cos(PI/6); // Inclinación 30°
    double posZ = radioOrbital * sin(anguloOrbital) * sin(PI/6);

    // Convertir a coordenadas ECEF si se solicita
    if (usarCoordenadasECEF) {
        double anguloRotacionTierra = VELOCIDAD_ROTACION_TIERRA * tiempoSegundos;
        double x_ecef = posX * cos(anguloRotacionTierra) - posY * sin(anguloRotacionTierra);
        double y_ecef = posX * sin(anguloRotacionTierra) + posY * cos(anguloRotacionTierra);
        posX = x_ecef;
        posY = y_ecef;
    }
    
    // Enviar tiempo orbital simulado (formato: código 6)
    String mensajeOrbita = "6:" + String(tiempoSegundos, 1);
    enviarConChecksum(mensajeOrbita);
}

// CONFIGURACIÓN INICIAL
void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);
  
  randomSeed(analogRead(0)); // Inicializar generador de números aleatorios
  
  // Inicializar parámetros orbitales
  proximaActualizacionOrbita = millis() + INTERVALO_ACTUALIZACION_ORBITA;
  radioOrbital = RADIO_TIERRA + ALTURA_SATELITE;
  periodoOrbitalReal = 2 * PI * sqrt(pow(radioOrbital, 3) / (CONSTANTE_GRAVITACIONAL * MASA_TIERRA));
  
  dht.begin(); // Inicializar sensor DHT
  
  // Configurar servo motor
  servoMotor.attach(SERVO);
  delay(100);
  servoMotor.write(0);  // Posición inicial
  delay(500);
  
  // Configurar pines del sensor ultrasónico
  pinMode(TRIGGER, OUTPUT);
  pinMode(ECHO, INPUT);
  digitalWrite(TRIGGER, LOW);
  
  // Inicializar buffer de temperaturas con ceros
  for (int i = 0; i < 10; i++) {
    bufferTemperaturas[i] = 0;
  }
  
  ultimoComandoRecibido = millis();
  enviarSimple("ESTACION: Sistema listo con verificación de checksum.");
}


long medirDistancia() {
  // Mide distancia con el sensor ultrasónico y si hay error o está fuera de rango manda -1 y se toma como error. Distancia (cm)

  digitalWrite(TRIGGER, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER, LOW);
  
  long duracionEco = pulseIn(ECHO, HIGH, 30000); // Medir tiempo de eco (timeout de 30ms para aproximadamente 5m máximo)
  if (duracionEco == 0) {
    // Timeout - no se detectó eco
    return -1;
  }
  
  long distanciaCm = duracionEco * 0.0343 / 2; // Calcular distancia (velocidad sonido aproximadamente 343 m/s)
  
  if (distanciaCm < 2 || distanciaCm > 400) { // Filtrar valores fuera de rango útil (2cm - 400cm)
    return -1;
  }
  
  return distanciaCm;
}


void actualizarPosicionServo() {
  // Actualiza la posición del servo 

  static bool servoDetenido = false;

  unsigned long tiempoActual = millis();

  // Si radar está desactivado, detener servo en posición central
  if (!enviarDatosRadar) {
    if (!servoDetenido) {
      servoMotor.write(90);   // Posición central
      servoDetenido = true;
    }
    return;
  }

  servoDetenido = false;

  // Actualizar ángulo según intervalo configurado
  if (tiempoActual - ultimoMovimientoRadar >= intervaloMovimientoRadar) {
    ultimoMovimientoRadar = tiempoActual;

    if (modoRastreoActivado) {
      // MODO BARRIDO: mover de 0° a 180° ida y vuelta
      servoMotor.write(anguloActual);

      anguloActual += pasoBarrido;
      if (anguloActual >= 180) {
        anguloActual = 180;
        pasoBarrido = -2;  // Cambiar dirección
      } else if (anguloActual <= 0) {
        anguloActual = 0;
        pasoBarrido = 2;   // Cambiar dirección
      }
    } else {
      // MODO ÁNGULO FIJO
      servoMotor.write(anguloFijo);
      anguloActual = anguloFijo;
    }
  }
}


float calcularMediaTemperaturas() {
  // Calcula la media de temperaturas almacenadas en buffer de temperaturas

  int cantidadMuestras = bufferTemperaturaLleno ? 10 : indiceBufferTemperatura;
  if (cantidadMuestras == 0) return 0;
  
  float sumaTotal = 0;
  for (int i = 0; i < cantidadMuestras; i++) {
    sumaTotal += bufferTemperaturas[i];
  }
  return sumaTotal / cantidadMuestras;
}


float calcularMediaHumedades() {
  // Calcula la media de humedades almacenadas en buffer de humedades
  int cantidadMuestras = bufferHumedadLleno ? 10 : indiceBufferHumedad;
  if (cantidadMuestras == 0) return 0;
  
  float sumaTotal = 0;
  for (int i = 0; i < cantidadMuestras; i++) {
    sumaTotal += bufferHumedades[i];
  }
  return sumaTotal / cantidadMuestras;
}


void procesarComando(String comandoCompleto) {
    // Procesa los comandos recibidos por serial con el formato código:valor
    Serial.println("RECIBIDO: " + comandoCompleto); // Mostrar comando recibido para depuración
    
    ultimoComandoRecibido = millis();
    
    // Separar código y valor
    int separador = comandoCompleto.indexOf(':');
    if (separador == -1) return;
    
    int codigoComando = comandoCompleto.substring(0, separador).toInt();
    String valorComando = comandoCompleto.substring(separador + 1);
    
    Serial.print("Procesando comando ");
    Serial.print(codigoComando);
    Serial.print(" valor ");
    Serial.println(valorComando);
    
    // Ejecutar acción según código de comando
    switch (codigoComando) {
      case 1: // Cambiar intervalo de envío DHT
        intervaloEnvioDHT = valorComando.toInt() * 1000UL;
        Serial.println(intervaloEnvioDHT);
        enviarSimple("5:OK");
        break;
        
      case 2: // Establecer ángulo fijo para servo
        anguloFijo = valorComando.toInt();
        if (anguloFijo < 0) anguloFijo = 0;
        if (anguloFijo > 180) anguloFijo = 180;
        modoRastreoActivado = false;
        servoMotor.write(anguloFijo);
        anguloActual = anguloFijo;
        Serial.print("Ángulo fijo: ");
        Serial.println(anguloFijo);
        enviarSimple("5:OK");
        break;
        
      case 3: // Cambiar intervalo de movimiento del radar
        intervaloMovimientoRadar = valorComando.toInt();
        Serial.print(intervaloMovimientoRadar);
        Serial.println("ms");
        enviarSimple("5:OK");
        break;
        
      case 6: // Seleccionar dónde se calcula la media
        calcularMediasEnSatelite = (valorComando.toInt() == 1);
        Serial.print("Cálculo media: ");
        Serial.println(calcularMediasEnSatelite ? "SATÉLITE" : "TIERRA");
        enviarSimple("5:OK");
        break;
        
      case 7: // Cambiar modo de radar (barrido/fijo)
        modoRastreoActivado = (valorComando.toInt() == 1);
        Serial.print("Modo: ");
        Serial.println(modoRastreoActivado ? "RASTREO" : "FIJO");
        enviarSimple("5:OK");
        break;
        
      case 8: // Configurar límite de temperatura (para futuras alarmas)
        Serial.print("Límite recibido: ");
        Serial.println(valorComando.toFloat());
        enviarSimple("5:OK");
        break;
        
      case 9: // Pausar/Reanudar envío de datos DHT
        enviarDatosDHT = (valorComando.toInt() == 1);
        Serial.println(enviarDatosDHT ? "DHT REANUDADO" : "DHT PAUSADO");
        enviarSimple("5:OK");
        break;
        
      case 10: // Pausar/Reanudar radar (sensor + servo)
        enviarDatosRadar = (valorComando.toInt() == 1);
        Serial.println(enviarDatosRadar ? "RADAR REANUDADO" : "RADAR PAUSADO (SERVO DETENIDO)");
        enviarSimple("5:OK");
        break;

      case 11: // Pausar/Reanudar simulación de órbita
        enviarDatosOrbita = (valorComando.toInt() == 1);
        Serial.print("Órbita: ");
        Serial.println(enviarDatosOrbita ? "REANUDADO" : "PAUSADO");
        enviarSimple("5:OK");
        break;
        
      case 12: // Cambiar intervalo de actualización de órbita
        INTERVALO_ACTUALIZACION_ORBITA = valorComando.toInt();
        Serial.print("Intervalo órbita: ");
        Serial.print(INTERVALO_ACTUALIZACION_ORBITA);
        Serial.println("ms");
        enviarSimple("5:OK");
        break;

      case 14: // Obtener temperatura actual (solicitud puntual)
        {
          float temperaturaInstantanea = dht.readTemperature();
          if (!isnan(temperaturaInstantanea)) {
            String mensajeTemperatura = "14:" + String(temperaturaInstantanea, 1);
            enviarConChecksum(mensajeTemperatura);
          } else {
            enviarSimple("0:ERROR_DHT");
          }
        }
        break;

      case 15: // Obtener todos los datos de sensores
        {
          float temperatura = dht.readTemperature();
          float humedad = dht.readHumidity();
          long distancia = medirDistancia();
          
          if (!isnan(temperatura) && !isnan(humedad) && distancia > 0) {
            String mensajeCompleto = "15:TEMP:" + String(temperatura, 1) +
                          ":HUM:" + String(humedad, 1) +
                          ":DIST:" + String(distancia) +
                          ":ANG:" + String(anguloActual);
            enviarConChecksum(mensajeCompleto);
          } else {
            enviarSimple("0:ERROR_SENSORES");
          }
        }
        break;
      
      case 16: // Pausar/Reanudar TODO el sistema
        {
          bool activarTodo = (valorComando.toInt() == 1);
          enviarDatosDHT = activarTodo;
          enviarDatosRadar = activarTodo;
          enviarDatosOrbita = activarTodo;
          sistemaTemperaturaIniciado = activarTodo;
          
          Serial.print("Todo: ");
          Serial.println(activarTodo ? "REANUDADO" : "PAUSADO");
          
          // Enviar estado completo del sistema
          String mensajeEstado = "13:DHT:" + String(enviarDatosDHT ? "1" : "0") +
                           ":RADAR:" + String(enviarDatosRadar ? "1" : "0") +
                           ":ORBITA:" + String(enviarDatosOrbita ? "1" : "0") +
                           ":MODO:" + String(modoRastreoActivado ? "1" : "0") +
                           ":ANGULO:" + String(anguloFijo) +
                           ":INTERVALO:" + String(intervaloEnvioDHT/1000);
          enviarConChecksum(mensajeEstado);
        }
        break;
        
      default: // Comando no reconocido
        Serial.print("Comando desconocido: ");
        Serial.println(codigoComando);
        enviarSimple("0:ComandoDesconocido");
        break;
    }
}

// PROGRAMA PRINCIPAL ______________________________________________________________________
void loop() {
  // Bucle principal del programa

  unsigned long tiempoActual = millis();
  
  // Verificar timeout de comunicación
  if (tiempoActual - ultimoComandoRecibido > TIMEOUT_COMUNICACION) {
    Serial.println("\nALERTA: Timeout de comunicación");
    enviarSimple("5:Timeout");
    ultimoComandoRecibido = tiempoActual;
  }
  
  // Actualizar simulación de órbita (si está activa)
  if (enviarDatosOrbita) {
    simularOrbita(tiempoActual, 0);
  }
  
  // Actualizar posición del servo (independiente del envío de datos)
  actualizarPosicionServo();
  
  // Enviar datos del radar (si está activo y pasó el intervalo)
  if (enviarDatosRadar && (tiempoActual - ultimoEnvioRadar >= intervaloEnvioRadar)) {
    ultimoEnvioRadar = tiempoActual;
    
    long distanciaMedida = medirDistancia();
    
    if (distanciaMedida > 0) {
      // Formato: código 4:ángulo : código 5:distancia
      
      String mensajeRadar = "4:" + String(anguloActual) + 
                          ":5:" + String(distanciaMedida);
      enviarConChecksum(mensajeRadar);
      Serial.println(mensajeRadar);
    } else if (distanciaMedida == -1) {
      enviarSimple("0:FalloRadar");
      Serial.println("ERROR: Fallo sensor radar");
    }
  }
  
  // Enviar datos DHT (si está activo y pasó el intervalo)
  if (enviarDatosDHT && (tiempoActual - ultimoEnvioDHT >= intervaloEnvioDHT)) {
    ultimoEnvioDHT = tiempoActual;
    
    float temperaturaActual = dht.readTemperature();
    float humedadActual = dht.readHumidity();
    
    // Verificar si el sensor DHT funciona
    if (isnan(temperaturaActual) || isnan(humedadActual)) {
      enviarSimple("0:FalloDHT");
      Serial.println("ERROR: Fallo sensor DHT");
      return;
    }

    //TEMPERATURA
    // Almacenar temperatura en buffer circular
    bufferTemperaturas[indiceBufferTemperatura] = temperaturaActual;
    indiceBufferTemperatura = (indiceBufferTemperatura + 1) % 10;
    if (!bufferTemperaturaLleno && indiceBufferTemperatura == 0) bufferTemperaturaLleno = true;
    
    temperaturaMediaActual = calcularMediaTemperaturas(); // Calcular media de temperaturas

    // Almacenar humedad en buffer circular
    bufferHumedades[indiceBufferHumedad] = humedadActual;
    indiceBufferHumedad = (indiceBufferHumedad + 1) % 10;
    if (!bufferHumedadLleno && indiceBufferHumedad == 0) bufferHumedadLleno = true;
    
    //HUMEDAD 
    // Calcular media de humedades
    humedadMediaActual = calcularMediaHumedades();
    
    // Preparar mensaje según configuración de cálculo de medias
    String mensajeDHT;
    if (calcularMediasEnSatelite) {
      // Formato: 1:temperatura : 2:humedad : 3:mediaTemp : mediaHum
      mensajeDHT = "1:" + String(temperaturaActual, 1) + 
                  ":2:" + String(humedadActual, 1) + 
                  ":3:" + String(temperaturaMediaActual, 1) +
                  ":" + String(humedadMediaActual, 1);
    } else {
      // Formato simple: 1:temperatura : 2:humedad
      mensajeDHT = "1:" + String(temperaturaActual, 1) + 
                  ":2:" + String(humedadActual, 1);
    }
    enviarConChecksum(mensajeDHT);
    Serial.println(mensajeDHT);
  }
  
  // Leer comandos recibidos por serial
  if (mySerial.available()) {
    String comandoRecibido = mySerial.readStringUntil('\n');
    comandoRecibido.trim();
    procesarComando(comandoRecibido);
  }
}
