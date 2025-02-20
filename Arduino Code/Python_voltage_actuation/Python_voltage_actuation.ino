const int voltagePin = A0;

const int redLEDPin = 6;
const int yellowLEDPin = 2;

const int HANDSHAKE = 0;
const int RED_LED_ON = 1;
const int Voltage_ON = 2;


String daqDelayStr;

int inByte = 0;

int daqDelay = 100;   // delay between acquisitions in milliseconds

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
  digitalWrite(redLEDPin, LOW);
  digitalWrite(yellowLEDPin, LOW);

  // initialize serial communication
  Serial.begin(115200);
}


void loop() {
  // If we're auto-transferring data (streaming mode)
  // Check if data has been sent to Arduino and respond accordingly
  if (Serial.available() > 0) {
    // Read in request
    inByte = Serial.read();

    // Handshake
    if (inByte == HANDSHAKE){
      if (Serial.availableForWrite()) {
          Serial.println("Handshake message received.");
      }
    }

    else if (inByte == RED_LED_ON)
     {
      digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
      delay(2000);                     // wait for a second
      digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
      delay(2000);}
    else if (inByte == Voltage_ON)
     {//wave.sine(freq);
      //wave.amplitude((Voltage_ON / 100) * 0.1);
      digitalWrite(LED_BUILTIN, HIGH);
      delay(500);
      digitalWrite(LED_BUILTIN, LOW);
      delay(500);
     } 
  }
}