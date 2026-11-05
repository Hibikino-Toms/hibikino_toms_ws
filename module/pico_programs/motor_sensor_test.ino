// Raspberry Pi Pico 2 W
// モーター・ポテンショメータ・エンコーダー動作確認プログラム
// シリアルモニタ：115200 bps
//
// 組み合わせ：
//   モーター1 + ポテンショメータ1（GP26 / ADC0）
//   モーター2 + ポテンショメータ2（GP27 / ADC1）
//   モーター3 + ポテンショメータ3（GP28 / ADC2）
//   モーター4 + エンコーダー4（A=GP8 / B=GP9）
//
// モーター出力：
//   M1 IN1=GP10, IN2=GP11
//   M2 IN1=GP12, IN2=GP13
//   M3 IN1=GP14, IN2=GP15
//   M4 IN1=GP16, IN2=GP17
//
// スタート・ストップスイッチ：GP18 - スイッチ - GND
// ポテンショメータ：各A端子=3V3、各B端子=AGND、C端子=ADC入力

const uint8_t MOTOR_COUNT = 4;
const uint8_t motorIn1[MOTOR_COUNT] = {10, 12, 14, 16};
const uint8_t motorIn2[MOTOR_COUNT] = {11, 13, 15, 17};

const uint8_t potentiometerPin[3] = {26, 27, 28};
const uint8_t encoder4A = 8;
const uint8_t encoder4B = 9;
const uint8_t startStopButtonPin = 18;

const uint16_t ADC_MAX_VALUE = 4095;
const float ADC_REFERENCE_VOLTAGE = 3.3f;

// 70% = 255 × 0.70 ≒ 179
const int MOTOR_TEST_PWM = 200;
const unsigned long MOTOR_STEP_TIME_MS = 1000;
const unsigned long SENSOR_PRINT_INTERVAL_MS = 200;

int motorCommand[MOTOR_COUNT] = {0, 0, 0, 0};

struct MotorTestStep {
  uint8_t motorIndex;
  int8_t direction;
};

// 各モーターを正転1秒、逆転1秒の順で動かす
const MotorTestStep motorTestSequence[MOTOR_COUNT * 2] = {
  {0,  1}, {0, -1},
  {1,  1}, {1, -1},
  {2,  1}, {2, -1},
  {3,  1}, {3, -1}
};

const uint8_t MOTOR_TEST_STEP_COUNT = sizeof(motorTestSequence) / sizeof(motorTestSequence[0]);

bool testRunning = false;
uint8_t currentStep = 0;
unsigned long currentStepStartedAt = 0;
unsigned long lastSensorPrintAt = 0;

// スイッチのデバウンス状態
bool buttonStablePressed = false;
bool buttonLastReadingPressed = false;
unsigned long buttonLastChangedAt = 0;
const unsigned long BUTTON_DEBOUNCE_MS = 30;

// エンコーダー4の状態・カウント
volatile int32_t encoder4Count = 0;
volatile uint8_t encoder4State = 0;
volatile int8_t encoder4QuarterCount = 0;

const int8_t encoderTransitionTable[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};

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

void applyCurrentTestStep() {
  stopAllMotors();

  uint8_t motorIndex = motorTestSequence[currentStep].motorIndex;
  int speed = motorTestSequence[currentStep].direction * MOTOR_TEST_PWM;
  motorCommand[motorIndex] = speed;
  setMotor(motorIn1[motorIndex], motorIn2[motorIndex], speed);

  Serial.print("[test] step ");
  Serial.print(currentStep + 1);
  Serial.print("/");
  Serial.print(MOTOR_TEST_STEP_COUNT);
  Serial.print(" M");
  Serial.print(motorIndex + 1);
  Serial.print(" ");
  Serial.print(speed > 0 ? "forward" : "reverse");
  Serial.print(" PWM=");
  Serial.println(abs(speed));
}

void startMotorTest() {
  testRunning = true;
  currentStep = 0;
  currentStepStartedAt = millis();
  Serial.println("[test] START");
  applyCurrentTestStep();
}

void stopMotorTest(const char *reason) {
  testRunning = false;
  stopAllMotors();
  Serial.print("[test] STOP: ");
  Serial.println(reason);
}

bool readButtonPressEvent() {
  bool readingPressed = digitalRead(startStopButtonPin) == LOW;

  if (readingPressed != buttonLastReadingPressed) {
    buttonLastChangedAt = millis();
    buttonLastReadingPressed = readingPressed;
  }

  if (millis() - buttonLastChangedAt >= BUTTON_DEBOUNCE_MS &&
      readingPressed != buttonStablePressed) {
    buttonStablePressed = readingPressed;
    return buttonStablePressed;
  }

  return false;
}

void updateMotorTest() {
  if (!testRunning) {
    return;
  }

  if (millis() - currentStepStartedAt < MOTOR_STEP_TIME_MS) {
    return;
  }

  currentStep++;

  if (currentStep >= MOTOR_TEST_STEP_COUNT) {
    stopMotorTest("sequence complete");
    return;
  }

  currentStepStartedAt = millis();
  applyCurrentTestStep();
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

void printPotentiometer(uint8_t number, uint16_t rawValue) {
  float voltage = (static_cast<float>(rawValue) * ADC_REFERENCE_VOLTAGE) /
                  static_cast<float>(ADC_MAX_VALUE);

  Serial.print("POT");
  Serial.print(number);
  Serial.print("=");
  Serial.print(rawValue);
  Serial.print("(");
  Serial.print(voltage, 2);
  Serial.print("V)");
}

void printSensorAndMotorStatus() {
  uint16_t potValue[3];
  int32_t encoderCountSnapshot;

  for (uint8_t i = 0; i < 3; i++) {
    potValue[i] = analogRead(potentiometerPin[i]);
  }

  noInterrupts();
  encoderCountSnapshot = encoder4Count;
  interrupts();

  Serial.print("[status] ");
  printPotentiometer(1, potValue[0]);
  Serial.print(" ");
  printPotentiometer(2, potValue[1]);
  Serial.print(" ");
  printPotentiometer(3, potValue[2]);
  Serial.print(" ENC4=");
  Serial.print(encoderCountSnapshot);
  Serial.print(" MOTOR_PWM=[");

  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    if (i > 0) {
      Serial.print(",");
    }
    Serial.print(motorCommand[i]);
  }

  Serial.print("] running=");
  Serial.print(testRunning ? "1" : "0");
  Serial.print(" step=");
  Serial.println(testRunning ? currentStep + 1 : 0);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  analogWriteRange(255);
  analogWriteFreq(20000);
  analogReadResolution(12);

  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    pinMode(motorIn1[i], OUTPUT);
    pinMode(motorIn2[i], OUTPUT);
  }
  stopAllMotors();

  for (uint8_t i = 0; i < 3; i++) {
    pinMode(potentiometerPin[i], INPUT);
  }

  pinMode(encoder4A, INPUT_PULLUP);
  pinMode(encoder4B, INPUT_PULLUP);
  encoder4State = (digitalRead(encoder4A) << 1) | digitalRead(encoder4B);
  attachInterrupt(digitalPinToInterrupt(encoder4A), updateEncoder4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoder4B), updateEncoder4, CHANGE);

  pinMode(startStopButtonPin, INPUT_PULLUP);
  buttonStablePressed = digitalRead(startStopButtonPin) == LOW;
  buttonLastReadingPressed = buttonStablePressed;
  buttonLastChangedAt = millis();

  Serial.println();
  Serial.println("=== Motor + Potentiometer + Encoder4 Test Start ===");
  Serial.println("POT1=GP26/ADC0, POT2=GP27/ADC1, POT3=GP28/ADC2");
  Serial.println("ENC4: A=GP8, B=GP9");
  Serial.println("Button: GP18 to GND");
  Serial.println("Press button to START/STOP the motor sequence.");
  Serial.println("All motors are stopped at startup.");
}

void loop() {
  if (readButtonPressEvent()) {
    if (testRunning) {
      stopMotorTest("button");
    } else {
      startMotorTest();
    }
  }

  updateMotorTest();

  if (millis() - lastSensorPrintAt >= SENSOR_PRINT_INTERVAL_MS) {
    lastSensorPrintAt = millis();
    printSensorAndMotorStatus();
  }

  delay(5);
}
