const int voltagePin = A0;

const int redLEDPin = 6;
const int yellowLEDPin = 2;
const int TTL_Pin = 4;

const int HANDSHAKE = 0;
const int VOLTAGE_REQUEST = 1;
const int TTL_Signal_ON = 2;
const int TTL_Signal_OFF = 3;

int inByte = 0;
int value;
unsigned long time_ms;


void printVoltage() {
  // read value from analog pin
  value = analogRead(voltagePin);
  time_ms = millis();

  // Write the result
  if (Serial.availableForWrite()) {
    String outstr = String(String(time_ms, DEC) + "," + String(value, DEC));
    Serial.println(outstr);
  }
}


#include "analogWave.h" // Include the library for analog waveform generation

analogWave wave(DAC);   // Create an instance of the analogWave class, using the DAC pin

int freq = 10;  // in hertz, change accordingly

void setup() {
  // Set LEDs to off
  pinMode(redLEDPin, OUTPUT);
  pinMode(yellowLEDPin, OUTPUT);
  pinMode(TTL_Pin, OUTPUT);           // set pin to input
  digitalWrite(TTL_Pin, HIGH);
  digitalWrite(redLEDPin, LOW);
  digitalWrite(yellowLEDPin, LOW);
  wave.sine(freq);       // Generate a sine wave with the initial frequency
  wave.amplitude(1);

  // initialize serial communication
  Serial.begin(115200);
}


void loop() {
  // If we're auto-transferring data (streaming mode)
  // Check if data has been sent to Arduino and respond accordingly
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "HELLO") {
        Serial.println("READY");  // Respond to handshake
    } 
    else 
    {
        
    inByte = command.toInt();

    // Handshake
    if (inByte == HANDSHAKE){
      if (Serial.availableForWrite()) {
          Serial.println("Handshake message received.");
      }
    }

    // If data is requested, fetch it and write it
    else if (inByte == VOLTAGE_REQUEST) printVoltage();

    else if (inByte == TTL_Signal_ON)
    {
      digitalWrite(TTL_Pin, LOW);
      digitalWrite(LED_BUILTIN, LOW);
      delay(1000);
      digitalWrite(LED_BUILTIN, HIGH);
      delay(500);
    }
    else if (inByte == TTL_Signal_OFF)
    {
      digitalWrite(TTL_Pin, HIGH);
      digitalWrite(LED_BUILTIN, LOW);
    }
    // else, turn LEDs on or off
    
  }
}
}