// Pico 2 W + TC78H653FTG x2 + DCモーター x4 + EC12E2420801 x4
// シリアルモニタ：115200 bps
//
// 配線：
//   Motor 1: IN1=GP10, IN2=GP11, Encoder A/B=GP2/GP3
//   Motor 2: IN1=GP12, IN2=GP13, Encoder A/B=GP4/GP5
//   Motor 3: IN1=GP14, IN2=GP15, Encoder A/B=GP6/GP7
//   Motor 4: IN1=GP16, IN2=GP17, Encoder A/B=GP8/GP9
//   通信確認用プッシュスイッチ：GP18 - スイッチ - GND
//
// pico_edf_button_esc_motor_foto_timeout.ino と同じ通信形式：
//   受信：mode,foto_val,edf_val\n
//   正常終了時の返答：mode + " " + 改行（例："2 \n"）
//   タイムアウト時の返答："666 " + 改行
//
// ee_debugでは、受信したコマンドの処理完了条件をプッシュスイッチで代用する。
// 例："2,900,1400\n"を受信後にスイッチを押すと、"2 \n"を返す。

const uint8_t MOTOR_COUNT = 4;

// TC78H653FTG D1：モーター1・2
// TC78H653FTG D2：モーター3・4
const uint8_t motorIn1[MOTOR_COUNT] = {10, 12, 14, 16};
const uint8_t motorIn2[MOTOR_COUNT] = {11, 13, 15, 17};

// EC12E2420801：中央共通端子 C はGND、A/Bは以下のGPIOへ接続
const uint8_t encoderA[MOTOR_COUNT] = {2, 4, 6, 8};
const uint8_t encoderB[MOTOR_COUNT] = {3, 5, 7, 9};

// 参照プログラムのupper_button_pin=18を、通信確認用ボタンとして使用
const uint8_t responseButtonPin = 18;

volatile int8_t encoderDelta[MOTOR_COUNT] = {0, 0, 0, 0};
volatile uint8_t encoderState[MOTOR_COUNT] = {0, 0, 0, 0};

int motorSpeed[MOTOR_COUNT] = {0, 0, 0, 0};  // -255 ～ +255

const int SPEED_STEP = 15;

// 2相エンコーダ用の状態遷移表
const int8_t transitionTable[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};

// 通信状態
bool communicationWaiting = false;
int pendingMode = -1;
int pendingFotoValue = 900;
int pendingEdfValue = 1400;
unsigned long commandStartedAt = 0;

// 参照プログラムと同じタイムアウト時間
const unsigned long MODE_1_TIMEOUT_MS = 5000;
const unsigned long OTHER_MODE_TIMEOUT_MS = 7000;

// 通信確認ボタンのデバウンス状態
bool buttonStablePressed = false;
bool buttonLastReadingPressed = false;
unsigned long buttonLastChangeAt = 0;
const unsigned long BUTTON_DEBOUNCE_MS = 30;

// USBシリアルはPCとの通信プロトコル専用にする。
// trueにするとデバッグログも出るが、PC側が応答と誤認するため通常はfalse。
const bool SERIAL_DEBUG_OUTPUT = false;

void updateEncoder(uint8_t index) {
  // 各エンコーダーの4逓倍相カウントを割り込み内で保持
  static int8_t count[MOTOR_COUNT] = {0, 0, 0, 0};

  uint8_t now = (digitalRead(encoderA[index]) << 1) | digitalRead(encoderB[index]);
  count[index] += transitionTable[(encoderState[index] << 2) | now];
  encoderState[index] = now;

  if (count[index] >= 4) {
    encoderDelta[index]++;
    count[index] = 0;
  } else if (count[index] <= -4) {
    encoderDelta[index]--;
    count[index] = 0;
  }
}

// attachInterrupt()用の割り込み関数
void readEncoder1() { updateEncoder(0); }
void readEncoder2() { updateEncoder(1); }
void readEncoder3() { updateEncoder(2); }
void readEncoder4() { updateEncoder(3); }

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

void printMotorStatus(uint8_t motorNumber, int change, int speed) {
  if (!SERIAL_DEBUG_OUTPUT) {
    return;
  }

  Serial.print("Motor ");
  Serial.print(motorNumber);
  Serial.print(" | encoder change: ");
  Serial.print(change);
  Serial.print(" | speed command: ");
  Serial.println(speed);
}

void printEncoderState(uint8_t encoderNumber, uint8_t state) {
  if (!SERIAL_DEBUG_OUTPUT) {
    return;
  }

  Serial.print("Initial ENC");
  Serial.print(encoderNumber);
  Serial.print(" A/B state: ");
  Serial.println(state, BIN);
}

// 参照プログラムと同じ返答形式（末尾に半角スペースを付ける）
void sendCommunicationResponse(int responseState) {
  String response = String(responseState) + " ";
  Serial.println(response);
}

// 受信した1行を、mode,foto_val,edf_valに分解する
bool parseCommunicationCommand(const String &line, int &mode, int &fotoValue, int &edfValue) {
  int firstComma = line.indexOf(',');
  int secondComma = line.indexOf(',', firstComma + 1);

  if (firstComma <= 0 || secondComma <= firstComma + 1) {
    return false;
  }

  mode = line.substring(0, firstComma).toInt();
  fotoValue = line.substring(firstComma + 1, secondComma).toInt();
  edfValue = line.substring(secondComma + 1).toInt();

  return mode >= 0 && mode <= 3;
}

void receiveCommunicationCommand() {
  if (Serial.available() <= 0) {
    return;
  }

  // 参照プログラムと同じく、改行までを1コマンドとして扱う
  String inputCommand = Serial.readStringUntil('\n');
  inputCommand.trim();

  int receivedMode;
  int receivedFotoValue;
  int receivedEdfValue;

  if (!parseCommunicationCommand(inputCommand, receivedMode, receivedFotoValue, receivedEdfValue)) {
    return;
  }

  // 参照プログラムは処理中に次のコマンドを受け付けないため、保留中は無視する
  if (communicationWaiting) {
    return;
  }

  pendingMode = receivedMode;
  pendingFotoValue = receivedFotoValue;
  pendingEdfValue = receivedEdfValue;
  commandStartedAt = millis();
  communicationWaiting = true;

  // pendingFotoValue / pendingEdfValueは、参照プログラムと同じ信号形式を
  // 保持するために受信している。ee_debugでは実機センサー/EDFを使わない。
}

// スイッチの押下エッジを検出。スイッチはINPUT_PULLUPで、押すとLOW。
bool responseButtonPressedEvent() {
  bool readingPressed = digitalRead(responseButtonPin) == LOW;

  if (readingPressed != buttonLastReadingPressed) {
    buttonLastChangeAt = millis();
    buttonLastReadingPressed = readingPressed;
  }

  if (millis() - buttonLastChangeAt >= BUTTON_DEBOUNCE_MS &&
      readingPressed != buttonStablePressed) {
    buttonStablePressed = readingPressed;
    return buttonStablePressed;
  }

  return false;
}

void processCommunicationState(bool buttonPressed) {
  if (!communicationWaiting) {
    return;
  }

  // 正常動作の完了条件は、コマンド受信後の「押下エッジ」のみ。
  // buttonStablePressedを条件に含めると、押しっぱなし状態で即時応答する。
  if (buttonPressed) {
    sendCommunicationResponse(pendingMode);
    communicationWaiting = false;
    pendingMode = -1;
    return;
  }

  // 参照プログラムと同じタイムアウト返答
  unsigned long timeoutMs = (pendingMode == 1)
                                ? MODE_1_TIMEOUT_MS
                                : OTHER_MODE_TIMEOUT_MS;

  if (millis() - commandStartedAt >= timeoutMs) {
    sendCommunicationResponse(666);
    communicationWaiting = false;
    pendingMode = -1;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (SERIAL_DEBUG_OUTPUT) {
    Serial.println();
    Serial.println("=== 4-Motor + 4-Encoder + Communication Debug Start ===");
  }

  analogWriteRange(255);
  analogWriteFreq(20000);

  // モーター出力を初期化
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    pinMode(motorIn1[i], OUTPUT);
    pinMode(motorIn2[i], OUTPUT);
    setMotor(motorIn1[i], motorIn2[i], 0);
  }

  // エンコーダー入力を初期化（外付け抵抗は不要）
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    pinMode(encoderA[i], INPUT_PULLUP);
    pinMode(encoderB[i], INPUT_PULLUP);
    encoderState[i] = (digitalRead(encoderA[i]) << 1) | digitalRead(encoderB[i]);
  }

  attachInterrupt(digitalPinToInterrupt(encoderA[0]), readEncoder1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderB[0]), readEncoder1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderA[1]), readEncoder2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderB[1]), readEncoder2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderA[2]), readEncoder3, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderB[2]), readEncoder3, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderA[3]), readEncoder4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderB[3]), readEncoder4, CHANGE);

  // 通信確認用プッシュスイッチを初期化
  // GP18とGNDの間に、通常開のプッシュスイッチを接続する。
  pinMode(responseButtonPin, INPUT_PULLUP);
  buttonStablePressed = digitalRead(responseButtonPin) == LOW;
  buttonLastReadingPressed = buttonStablePressed;
  buttonLastChangeAt = millis();

  // 起動時のエンコーダー状態をデバッグ表示
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    printEncoderState(i + 1, encoderState[i]);
  }

  if (SERIAL_DEBUG_OUTPUT) {
    Serial.println("Rotate an encoder to control its motor.");
    Serial.println("Motor 1/2 use TC78H653FTG D1; Motor 3/4 use D2.");
    Serial.println("Comm RX: mode,foto_val,edf_val; press GP18 switch for normal response.");
  }
}

void loop() {
  static unsigned long lastStatusTime = 0;

  int8_t change[MOTOR_COUNT];
  uint8_t currentState[MOTOR_COUNT];

  // ボタン状態はコマンド待ちでないときも更新する。
  // これにより、コマンド受信前から押されていたボタンを新しい押下として扱わない。
  bool buttonPressed = responseButtonPressedEvent();

  // シリアル通信を参照プログラムと同じ形式で処理
  receiveCommunicationCommand();
  processCommunicationState(buttonPressed);

  noInterrupts();
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    change[i] = encoderDelta[i];
    currentState[i] = encoderState[i];
    encoderDelta[i] = 0;
  }
  interrupts();

  // 各エンコーダーの回転量で、対応するモーターの速度を変更
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    if (change[i] != 0) {
      motorSpeed[i] = constrain(motorSpeed[i] + change[i] * SPEED_STEP, -255, 255);
      setMotor(motorIn1[i], motorIn2[i], motorSpeed[i]);
      printMotorStatus(i + 1, change[i], motorSpeed[i]);
    }
  }

  // デバッグログは通常の通信プロトコルと混ざらないよう抑制する。
  if (SERIAL_DEBUG_OUTPUT && millis() - lastStatusTime >= 1000) {
    lastStatusTime = millis();

    Serial.print("[status]");
    for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
      Serial.print(" ENC");
      Serial.print(i + 1);
      Serial.print(" A/B=");
      Serial.print(currentState[i], BIN);
      Serial.print(" speed");
      Serial.print(i + 1);
      Serial.print("=");
      Serial.print(motorSpeed[i]);
    }
    Serial.println();
  }

  delay(5);
}
