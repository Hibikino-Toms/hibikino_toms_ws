#include <hardware/clocks.h>
#include <hardware/gpio.h>
#include <hardware/pwm.h>

// Raspberry Pi Pico 2 W: モーター・センサー・FB5311M-360 動作確認
// シリアルモニター: 115200 bps
//
// 使用するモーター:
//   M1: TC78H653FTG IN1=GP10, IN2=GP11
//   M2: TC78H653FTG IN1=GP12, IN2=GP13
//   M3/M4は使用しない
//
// センサー:
//   POT1: GP26 / ADC0 (A=3V3, B=AGND, C=GP26)
//   M2用エンコーダー4: A=GP8, B=GP9, 共通端子=GND
//   FB5311M-360 フィードバック: GP28 / ADC2
//
// サーボ:
//   制御信号=GP17、フィードバック=GP28
//   GP17は制御信号専用。サーボ電源は別電源を使い、GNDをPicoと共通にする。
//   停止指令は1500us、テスト回転指令は1600us / 1400us。
//
// NCリミットスイッチ:
//   GP19 -- COM/NC接点 -- GND
//   INPUT_PULLUP使用。通常(接点閉)=LOW、作動または断線(接点開)=HIGH。
//   HIGHになったらモーターを停止し、サーボへ停止指令を出す。
//
// シリアルコマンド:
//   s: テスト開始 (M1正逆、M2正逆、サーボ正逆を各1秒)
//   x: テスト中止

constexpr uint8_t MOTOR_COUNT = 2;
constexpr uint8_t motorIn1[MOTOR_COUNT] = {10, 12};
constexpr uint8_t motorIn2[MOTOR_COUNT] = {11, 13};

constexpr uint8_t potentiometer1Pin = 26;
constexpr uint8_t encoder4A = 8;
constexpr uint8_t encoder4B = 9;
constexpr uint8_t servoControlPin = 17;
constexpr uint8_t servoFeedbackPin = 28;
constexpr uint8_t limitSwitchPin = 19;

constexpr uint16_t ADC_MAX_VALUE = 4095;
constexpr float ADC_REFERENCE_VOLTAGE = 3.3f;
constexpr int MOTOR_TEST_PWM = 200;  // Approximately 78% of 255
constexpr int SERVO_NEUTRAL_US = 1500;
constexpr int SERVO_CW_TEST_US = 1600;
constexpr int SERVO_CCW_TEST_US = 1400;
constexpr unsigned long TEST_STEP_TIME_MS = 1000;
constexpr unsigned long SENSOR_PRINT_INTERVAL_MS = 200;

int motorCommand[MOTOR_COUNT] = {0, 0};
int servoCommandUs = SERVO_NEUTRAL_US;
uint servoPwmSlice = 0;
float servoPwmDivider = 1.0f;
bool servoPwmReady = false;
constexpr uint16_t SERVO_PWM_WRAP = 59999;
constexpr uint32_t SERVO_PWM_FREQUENCY_HZ = 50;

enum TestTarget : uint8_t {
  MOTOR_1 = 0,
  MOTOR_2 = 1,
  SERVO = 2
};

struct TestStep {
  TestTarget target;
  int command;  // モーターは符号付きPWM、サーボはパルス幅(us)
};

const TestStep testSequence[] = {
  {MOTOR_1,  MOTOR_TEST_PWM},
  {MOTOR_1, -MOTOR_TEST_PWM},
  {MOTOR_2,  MOTOR_TEST_PWM},
  {MOTOR_2, -MOTOR_TEST_PWM},
  {SERVO,    SERVO_CW_TEST_US},
  {SERVO,    SERVO_CCW_TEST_US}
};
constexpr uint8_t TEST_STEP_COUNT = sizeof(testSequence) / sizeof(testSequence[0]);

bool testRunning = false;
uint8_t currentStep = 0;
unsigned long currentStepStartedAt = 0;
unsigned long lastSensorPrintAt = 0;

// エンコーダー4の状態・カウント。モーター2の回転確認に使用。
volatile int32_t encoder4Count = 0;
volatile uint8_t encoder4State = 0;
volatile int8_t encoder4QuarterCount = 0;

const int8_t encoderTransitionTable[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};

void setMotor(uint8_t motorIndex, int speed) {
  speed = constrain(speed, -255, 255);

  if (speed > 0) {
    analogWrite(motorIn1[motorIndex], speed);
    digitalWrite(motorIn2[motorIndex], LOW);
  } else if (speed < 0) {
    digitalWrite(motorIn1[motorIndex], LOW);
    analogWrite(motorIn2[motorIndex], -speed);
  } else {
    digitalWrite(motorIn1[motorIndex], LOW);
    digitalWrite(motorIn2[motorIndex], LOW);
  }
  motorCommand[motorIndex] = speed;
}

uint16_t servoPulseToLevel(int pulseWidthUs) {
  pulseWidthUs = constrain(pulseWidthUs, 500, 2500);
  const float pwmClockHz = static_cast<float>(clock_get_hz(clk_sys)) /
                           servoPwmDivider;
  return static_cast<uint16_t>(pwmClockHz * pulseWidthUs / 1000000.0f);
}

void writeServoPulse(int pulseWidthUs) {
  servoCommandUs = constrain(pulseWidthUs, 500, 2500);
  if (servoPwmReady) {
    pwm_set_gpio_level(servoControlPin, servoPulseToLevel(servoCommandUs));
  }
}

void initializeServoPWM() {
  gpio_set_function(servoControlPin, GPIO_FUNC_PWM);
  servoPwmSlice = pwm_gpio_to_slice_num(servoControlPin);

  pwm_config config = pwm_get_default_config();
  servoPwmDivider = static_cast<float>(clock_get_hz(clk_sys)) /
                    (SERVO_PWM_FREQUENCY_HZ * (SERVO_PWM_WRAP + 1.0f));
  pwm_config_set_clkdiv(&config, servoPwmDivider);
  pwm_config_set_wrap(&config, SERVO_PWM_WRAP);
  pwm_init(servoPwmSlice, &config, false);

  servoPwmReady = true;
  writeServoPulse(SERVO_NEUTRAL_US);
  pwm_set_enabled(servoPwmSlice, true);
}

void stopAllOutputs() {
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    setMotor(i, 0);
  }
  writeServoPulse(SERVO_NEUTRAL_US);
}

bool limitIsTripped() {
  // NC接点が開く(または配線が切れる)と内部プルアップでHIGHになる。
  return digitalRead(limitSwitchPin) == HIGH;
}

void printCurrentStep() {
  const TestStep &step = testSequence[currentStep];
  stopAllOutputs();

  if (step.target == SERVO) {
    writeServoPulse(step.command);
    Serial.print("[test] step ");
    Serial.print(currentStep + 1);
    Serial.print("/");
    Serial.print(TEST_STEP_COUNT);
    Serial.print(" SERVO command=");
    Serial.print(servoCommandUs);
    Serial.println(" us");
  } else {
    const uint8_t motorIndex = static_cast<uint8_t>(step.target);
    setMotor(motorIndex, step.command);
    Serial.print("[test] step ");
    Serial.print(currentStep + 1);
    Serial.print("/");
    Serial.print(TEST_STEP_COUNT);
    Serial.print(" M");
    Serial.print(motorIndex + 1);
    Serial.print(step.command > 0 ? " forward PWM=" : " reverse PWM=");
    Serial.println(abs(step.command));
  }
}

void stopTest(const char *reason) {
  testRunning = false;
  stopAllOutputs();
  Serial.print("[test] STOP: ");
  Serial.println(reason);
}

void startTest() {
  if (limitIsTripped()) {
    stopAllOutputs();
    Serial.println("[test] START refused: NC limit switch is open/tripped (GP19=HIGH)");
    return;
  }

  testRunning = true;
  currentStep = 0;
  currentStepStartedAt = millis();
  Serial.println("[test] START");
  printCurrentStep();
}

void updateTest() {
  if (!testRunning) {
    return;
  }

  if (limitIsTripped()) {
    stopTest("NC limit switch open or wiring disconnected");
    return;
  }

  if (millis() - currentStepStartedAt < TEST_STEP_TIME_MS) {
    return;
  }

  currentStep++;
  if (currentStep >= TEST_STEP_COUNT) {
    stopTest("sequence complete");
    return;
  }

  currentStepStartedAt = millis();
  printCurrentStep();
}

void processSerialCommands() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    if (command == 's' || command == 'S') {
      if (testRunning) {
        Serial.println("[test] already running; send x to stop");
      } else {
        startTest();
      }
    } else if (command == 'x' || command == 'X') {
      stopTest("serial command x");
    }
  }
}

void updateEncoder4() {
  const uint8_t now = (digitalRead(encoder4A) << 1) | digitalRead(encoder4B);
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

void printAnalogValue(const char *label, uint16_t rawValue) {
  const float voltage = static_cast<float>(rawValue) * ADC_REFERENCE_VOLTAGE /
                        static_cast<float>(ADC_MAX_VALUE);
  Serial.print(label);
  Serial.print('=');
  Serial.print(rawValue);
  Serial.print("(");
  Serial.print(voltage, 3);
  Serial.print("V)");
}

void printStatus() {
  const uint16_t pot1Value = analogRead(potentiometer1Pin);
  const uint16_t servoFeedbackValue = analogRead(servoFeedbackPin);
  int32_t encoderCountSnapshot;

  noInterrupts();
  encoderCountSnapshot = encoder4Count;
  interrupts();

  Serial.print("[status] ");
  printAnalogValue("POT1", pot1Value);
  Serial.print(" ENC4(M2)=");
  Serial.print(encoderCountSnapshot);
  Serial.print(' ');
  printAnalogValue("SERVO_FB", servoFeedbackValue);
  Serial.print(" SERVO_CMD=");
  Serial.print(servoCommandUs);
  Serial.print("us MOTOR_PWM=[");
  Serial.print(motorCommand[0]);
  Serial.print(',');
  Serial.print(motorCommand[1]);
  Serial.print("] LIMIT=");
  Serial.print(limitIsTripped() ? "TRIPPED/OPEN" : "OK/CLOSED");
  Serial.print(" running=");
  Serial.print(testRunning ? '1' : '0');
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
  initializeServoPWM();
  stopAllOutputs();

  pinMode(potentiometer1Pin, INPUT);
  pinMode(servoFeedbackPin, INPUT);

  pinMode(encoder4A, INPUT_PULLUP);
  pinMode(encoder4B, INPUT_PULLUP);
  encoder4State = (digitalRead(encoder4A) << 1) | digitalRead(encoder4B);
  attachInterrupt(digitalPinToInterrupt(encoder4A), updateEncoder4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoder4B), updateEncoder4, CHANGE);

  pinMode(limitSwitchPin, INPUT_PULLUP);

  Serial.println();
  Serial.println("=== M1/M2 + POT1 + Encoder4 + FB5311M-360 test ===");
  Serial.println("M1: IN1=GP10 IN2=GP11 | M2: IN1=GP12 IN2=GP13");
  Serial.println("POT1: GP26/ADC0 | ENC4 for M2: A=GP8 B=GP9");
  Serial.println("Servo: signal=GP17 feedback=GP28/ADC2 (neutral=1500us)");
  Serial.println("NC limit: GP19 to GND through COM/NC; LOW=closed, HIGH=open/tripped");
  Serial.println("Send 's' to start; send 'x' to stop. Limit opening stops the test.");
  Serial.println("Motors and servo are commanded to stop at startup.");
}

void loop() {
  processSerialCommands();
  updateTest();

  if (millis() - lastSensorPrintAt >= SENSOR_PRINT_INTERVAL_MS) {
    lastSensorPrintAt = millis();
    printStatus();
  }

  delay(2);
}
