// Raspberry Pi Pico 2 W: ROS2 USB-serial end-effector motor teleoperation
// Pin layout follows motor_sensor_test.ino.
// Motors: M1 GP10/11, M2 GP12/13, M3 GP14/15, M4 GP16/17
// Pots: GP26/ADC0, GP27/ADC1, GP28/ADC2; ENC4: A=GP8, B=GP9
// Commands: M<motor>,<signed PWM> (e.g. M2,-180), or STOP; 115200 baud.

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

const uint8_t MOTOR_COUNT = 4;
const uint8_t motorIn1[MOTOR_COUNT] = {10, 12, 14, 16};
const uint8_t motorIn2[MOTOR_COUNT] = {11, 13, 15, 17};
const uint8_t potentiometerPin[3] = {26, 27, 28};
const uint8_t encoder4A = 8;
const uint8_t encoder4B = 9;
const unsigned long SENSOR_PRINT_INTERVAL_MS = 200;
const unsigned long COMMAND_WATCHDOG_MS = 600;
const uint16_t ADC_MAX_VALUE = 4095;
const float ADC_REFERENCE_VOLTAGE = 3.3f;

int motorCommand[MOTOR_COUNT] = {0, 0, 0, 0};
volatile int32_t encoder4Count = 0;
volatile int8_t encoder4QuarterCount = 0;
volatile uint8_t encoder4State = 0;
const int8_t encoderTransitionTable[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};
char commandBuffer[32];
uint8_t commandLength = 0;
unsigned long lastSensorPrintAt = 0;
unsigned long lastCommandAt = 0;

void setMotor(uint8_t in1, uint8_t in2, int speed) {
  speed = constrain(speed, -255, 255);
  if (speed > 0) {
    analogWrite(in1, speed);
    digitalWrite(in2, LOW);
  } else if (speed < 0) {
    digitalWrite(in1, LOW);
    analogWrite(in2, -speed);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
  }
}

void stopAllMotors() {
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    motorCommand[i] = 0;
    setMotor(motorIn1[i], motorIn2[i], 0);
  }
}

void updateEncoder4() {
  uint8_t now = (digitalRead(encoder4A) << 1) | digitalRead(encoder4B);
  encoder4QuarterCount += encoderTransitionTable[(encoder4State << 2) | now];
  encoder4State = now;
  if (encoder4QuarterCount >= 4) {
    encoder4Count++;
    encoder4QuarterCount = 0;
  } else if (encoder4QuarterCount <= -4) {
    encoder4Count--;
    encoder4QuarterCount = 0;
  }
}

void applyMotorCommand(const char *command) {
  if (strcmp(command, "STOP") == 0) {
    stopAllMotors();
    lastCommandAt = millis();
    return;
  }
  if (strcmp(command, "KEEPALIVE") == 0) {
    lastCommandAt = millis();
    return;
  }
  if (strcmp(command, "ZERO_ENC4") == 0) {
    bool stopped = true;
    for (uint8_t i = 0; i < MOTOR_COUNT; i++) stopped &= motorCommand[i] == 0;
    if (stopped) {
      noInterrupts();
      encoder4Count = 0;
      encoder4QuarterCount = 0;
      interrupts();
    }
    lastCommandAt = millis();
    return;
  }

  // Atomic parallel drive for automatic return-to-home. The legacy M command
  // below deliberately keeps its original one-motor-at-a-time behavior.
  int drive[MOTOR_COUNT];
  char trailing = '\0';
  if (sscanf(command, "DRIVE %d,%d,%d,%d%c", &drive[0], &drive[1], &drive[2],
             &drive[3], &trailing) == 4) {
    for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
      motorCommand[i] = constrain(drive[i], -255, 255);
      setMotor(motorIn1[i], motorIn2[i], motorCommand[i]);
    }
    lastCommandAt = millis();
    return;
  }

  int motorNumber = 0;
  int pwm = 0;
  trailing = '\0';
  if (sscanf(command, "M%d,%d%c", &motorNumber, &pwm, &trailing) != 2 ||
      motorNumber < 1 || motorNumber > MOTOR_COUNT) {
    return;
  }

  // Only one motor may run at a time.
  stopAllMotors();
  uint8_t index = static_cast<uint8_t>(motorNumber - 1);
  motorCommand[index] = constrain(pwm, -255, 255);
  setMotor(motorIn1[index], motorIn2[index], motorCommand[index]);
  lastCommandAt = millis();
}

void receiveCommands() {
  while (Serial.available() > 0) {
    char incoming = static_cast<char>(Serial.read());
    if (incoming == '\r') continue;
    if (incoming == '\n') {
      commandBuffer[commandLength] = '\0';
      applyMotorCommand(commandBuffer);
      commandLength = 0;
    } else if (commandLength < sizeof(commandBuffer) - 1) {
      commandBuffer[commandLength++] = incoming;
    } else {
      commandLength = 0;
    }
  }
}

void printStatus() {
  uint16_t pot1 = analogRead(potentiometerPin[0]);
  uint16_t pot2 = analogRead(potentiometerPin[1]);
  uint16_t pot3 = analogRead(potentiometerPin[2]);
  int32_t encoderCountSnapshot;
  noInterrupts();
  encoderCountSnapshot = encoder4Count;
  interrupts();

  Serial.print("[STATUS] PWM=");
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    if (i > 0) Serial.print(',');
    Serial.print(motorCommand[i]);
  }
  Serial.print(" ENC4=");
  Serial.print(encoderCountSnapshot);
  Serial.print(" POT1=");
  Serial.print(pot1);
  Serial.print(',');
  Serial.print((static_cast<float>(pot1) * ADC_REFERENCE_VOLTAGE) / ADC_MAX_VALUE, 2);
  Serial.print("V POT2=");
  Serial.print(pot2);
  Serial.print(',');
  Serial.print((static_cast<float>(pot2) * ADC_REFERENCE_VOLTAGE) / ADC_MAX_VALUE, 2);
  Serial.print("V POT3=");
  Serial.print(pot3);
  Serial.print(',');
  Serial.print((static_cast<float>(pot3) * ADC_REFERENCE_VOLTAGE) / ADC_MAX_VALUE, 2);
  Serial.println('V');
}

void setup() {
  Serial.begin(115200);
  analogWriteRange(255);
  analogWriteFreq(20000);
  analogReadResolution(12);
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    pinMode(motorIn1[i], OUTPUT);
    pinMode(motorIn2[i], OUTPUT);
  }
  stopAllMotors();
  lastCommandAt = millis();
  for (uint8_t i = 0; i < 3; i++) pinMode(potentiometerPin[i], INPUT);
  pinMode(encoder4A, INPUT_PULLUP);
  pinMode(encoder4B, INPUT_PULLUP);
  encoder4State = (digitalRead(encoder4A) << 1) | digitalRead(encoder4B);
  attachInterrupt(digitalPinToInterrupt(encoder4A), updateEncoder4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoder4B), updateEncoder4, CHANGE);
}

void loop() {
  receiveCommands();
  bool anyMotorRunning = false;
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) anyMotorRunning |= motorCommand[i] != 0;
  if (anyMotorRunning && millis() - lastCommandAt > COMMAND_WATCHDOG_MS) {
    stopAllMotors();
  }
  if (millis() - lastSensorPrintAt >= SENSOR_PRINT_INTERVAL_MS) {
    lastSensorPrintAt = millis();
    printStatus();
  }
  delay(2);
}
