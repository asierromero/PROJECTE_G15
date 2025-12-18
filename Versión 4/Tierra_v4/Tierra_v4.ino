#include <SoftwareSerial.h>

// Configurar comunicación serial software (RX, TX)
SoftwareSerial mySerial(10, 11); // Pin 10 como RX, Pin 11 como TX

const int BUZZER = 3;    // Pin del buzzer para alarmas sonoras
const int led1 = 13;     // LED verde - indica recepción de datos
const int led2 = 12;     // LED rojo - indica errores o fallos

// VARIABLES DE CONTROL DE SISTEMA
unsigned long lastDataTime = 0;        // Último tiempo de recepción de datos
const unsigned long LED_DELAY = 100;   // Tiempo LED encendido (ms)


bool verificarChecksum(String mensaje) {
  // Verificar checksum

    int ultimoSeparador = mensaje.lastIndexOf(':');
    if (ultimoSeparador == -1) return false;

    String datos = mensaje.substring(0, ultimoSeparador);
    String checksumStr = mensaje.substring(ultimoSeparador + 1);

    // Verificar que el checksum es numérico
    for (unsigned int i = 0; i < checksumStr.length(); i++) {
        if (!isdigit(checksumStr[i])) return false;
    }

    int checksumRecibido = checksumStr.toInt();

    // Calcular checksum EXACTAMENTE IGUAL que el satélite
    int checksumCalculado = 0;
    for (unsigned int i = 0; i < datos.length(); i++) {
        checksumCalculado += (int)datos[i];
    }
    checksumCalculado %= 256;

    return checksumCalculado == checksumRecibido;
}


// CONFIGURACIÓN INICIAL
void setup() {
   Serial.begin(9600); // Inicializar comunicación serial CON PYTHON
   
   mySerial.begin(9600); // Inicializar comunicación con SATÉLITE
   
   // Configurar pines de salida
   pinMode(BUZZER, OUTPUT);
   pinMode(led1, OUTPUT);
   pinMode(led2, OUTPUT);
   
   // Estado inicial de los LEDs
   digitalWrite(led1, LOW);
   digitalWrite(led2, LOW);
   noTone(BUZZER);
   
   // Mensaje de inicio
   Serial.println("ESTACION: Sistema listo con verificación de checksum.");
}

// PROGRAMA PRINCIPAL _________________________________________________________
void loop() {
   // RECEPCIÓN DE DATOS DEL SATELITE 
   if (mySerial.available()) {
      String data = mySerial.readStringUntil('\n');
      data.trim();
       lastDataTime = millis(); 
      
      if (data.length() == 0) return;
      
      // Mostrar lo que recibimos para depuración
      // Serial.println("<- SAT: " + data);
      
      // MENSAJES DE ERROR
      if (data.startsWith("0:") || (millis() - lastDataTime > 10000)) {
         Serial.println(data);
         digitalWrite(led2, HIGH);
         digitalWrite(led1, LOW);
         tone(BUZZER, 800, 500);
         delay(50);
         digitalWrite(led2, LOW);
         noTone(BUZZER);
         return;
      }
      
      // MENSAJES DE CONFIRMACIÓN ( sin checksum )
      if (data.startsWith("5:")) {
         Serial.println(data);
         digitalWrite(led1, HIGH);
         delay(20);
         digitalWrite(led1, LOW);
         return;
      }
      
      // MENSAJE DE DATOS ( con checksum )
      // Tipos de mensajes que pueden tener checksum
      if (data.startsWith("1:") || data.startsWith("4:") || data.startsWith("6:") || 
          data.startsWith("13:") || data.startsWith("14:") || data.startsWith("15:")) {
         
         // Verificar si tiene checksum (último campo es numérico)
         int ultimoSeparador = data.lastIndexOf(':');
         if (ultimoSeparador == -1) {
            // Sin checksum, reenviar tal cual
            Serial.println(data);
            digitalWrite(led1, HIGH);
            delay(20);
            digitalWrite(led1, LOW);
            return;
         }
         
         String posibleChecksum = data.substring(ultimoSeparador + 1);
         bool tieneChecksum = true;
         
         // Verificar si el último campo es numérico (es un checksum)
         for (unsigned int i = 0; i < posibleChecksum.length(); i++) {
            if (!isdigit(posibleChecksum[i])) {
               tieneChecksum = false;
               break;
            }
         }
         
         if (tieneChecksum) {
            if (verificarChecksum(data)) {
               // Checksum correcto
               Serial.println(data);
               digitalWrite(led1, HIGH);
               lastDataTime = millis();
               delay(20);
               digitalWrite(led1, LOW);
            } else {
               // Checksum incorrecto - enviar mensaje de error pero también el dato
               String datosSinChecksum = data.substring(0, ultimoSeparador);
               Serial.println("ERROR: Checksum incorrecto en: " + datosSinChecksum);
               digitalWrite(led2, HIGH);
               tone(BUZZER, 600, 200);
               delay(100);
               digitalWrite(led2, LOW);
               noTone(BUZZER);
               
               // También enviar los datos para que Python pueda procesarlos
               Serial.println(datosSinChecksum);
            }
         } else {
            // No tiene checksum, reenviar tal cual
            Serial.println(data);
            digitalWrite(led1, HIGH);
            delay(20);
            digitalWrite(led1, LOW);
         }
         
         return;
      }
      
      // MENSAJES DEL SISTEMA
      if (data.startsWith("ESTACION:")) {
         Serial.println(data);
         return;
      }
      
      // CUALQUIER OTRO MENSAJE
      Serial.println(data);
      digitalWrite(led1, HIGH);
      delay(20);
      digitalWrite(led1, LOW);
   }
   
   // REENVÍO DE COMANDOS DE PYTHON AL SATÉLITE 
   if (Serial.available()) {
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();
      
      if (cmd.length() > 0) {
         mySerial.println(cmd);
         Serial.println("-> SAT: " + cmd);
      }
   }
   
   // Apagar LED después de un tiempo sin datos
   if (millis() - lastDataTime > 1000) {
      digitalWrite(led1, LOW);
      digitalWrite(led2, LOW);
   }
}