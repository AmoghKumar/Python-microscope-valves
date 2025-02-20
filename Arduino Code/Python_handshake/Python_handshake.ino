const int voltagePin = A0;

const int redLEDPin = 6;
const int yellowLEDPin = 2;

const int HANDSHAKE = 0;
const int VOLTAGE_REQUEST = 1;
const int RED_LED_ON = 2;
const int RED_LED_OFF = 3;
const int YELLOW_LED_ON = 4;
const int YELLOW_LED_OFF = 5;

const int ON_REQUEST = 6;
const int STREAM = 7;
const int READ_DAQ_DELAY = 8;

String daqDelayStr;

int inByte = 0;
int daqMode = ON_REQUEST;
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
  if (daqMode == STREAM) {
    printVoltage();
    delay(daqDelay);
  }

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

    // If data is requested, fetch it and write it
    else if (inByte == VOLTAGE_REQUEST) printVoltage();

    // Switch daqMode
    else if (inByte == ON_REQUEST) daqMode = ON_REQUEST;
    else if (inByte == STREAM) daqMode = STREAM;

    // Read in DAQ delay
    else if (inByte == READ_DAQ_DELAY) {
      while (Serial.available() == 0) ;
      daqDelayStr = Serial.readStringUntil('x');
      daqDelay = daqDelayStr.toInt();
    }

    // else, turn LEDs on or off
    else if (inByte == RED_LED_ON)
     {
      digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
      delay(500);                      // wait for a second
      digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
      delay(1000);}
    else if (inByte == RED_LED_OFF) digitalWrite(redLEDPin, LOW);
    else if (inByte == YELLOW_LED_ON)
     {wave.sine(freq);
      wave.stop();
     digitalWrite(LED_BUILTIN, LOW);
     delay(1000);
     digitalWrite(LED_BUILTIN, HIGH);
     delay(500);
     } 
    else if (inByte == YELLOW_LED_OFF) digitalWrite(yellowLEDPin, LOW);
  }
}