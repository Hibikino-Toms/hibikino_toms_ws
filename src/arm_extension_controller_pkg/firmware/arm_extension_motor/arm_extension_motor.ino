// CBA-30 / PDBA-30F + Pico 2 W. ROS用専用スケッチ。
// GP14=F(戻す), GP15=R(伸ばす), GP16=原点NC, GP17=SPEED変換回路。
// 既存のキーボード用スケッチとは別。単相SPEEDなので方向は指令から推定。
#include <math.h>
#include <stdio.h>

const int F_PIN = 14, R_PIN = 15, HOME_PIN = 16, SPEED_PIN = 17;
const float MM_PER_PULSE = 3.14159265358979323846f * 2 * 15 / (12 * 50);
const unsigned long REST_MS = 10000, WATCHDOG_MS = 300;
const unsigned long RUN_TIMEOUT_MS = 10000, STALL_MS = 1000;
volatile long steps = 0;
volatile int direction = 0;
volatile unsigned long pulses = 0, lastPulseAt = 0;
volatile bool referenced = false;
enum State { IDLE, MOVING, SETTLING };
State state = IDLE;
float maxPosition = 0, maxMove = 0, startPosition = 0, requested = 0;
unsigned long activeId = 0, startedAt = 0, stoppedAt = 0, lastHeartbeat = 0;
unsigned long homeClosedAt = 0;
// homeActive is also read by the SPEED interrupt.  At a held home switch,
// post-stop encoder pulses must not erase the just-established origin.
volatile bool homeActive = true;
bool lastHomeOpen = true, resultSuccess = false, homing = false;
const char *resultReason = "NONE";
char buffer[96];
unsigned int used = 0;
bool discardLine = false;

void countPulse() {
  ++pulses;
  lastPulseAt = millis();
  if (referenced) {
    if (direction == 0 && homeActive) {
      // The mechanism is physically at the home switch.  Ignore residual/noise
      // SPEED pulses rather than losing the newly established 0 mm reference.
    } else if (direction == 0) referenced = false;
    else steps += direction;
  }
}

float positionMm() {
  noInterrupts();
  long value = steps;
  interrupts();
  return value * MM_PER_PULSE;
}

unsigned long lastPulseTime() {
  noInterrupts();
  unsigned long value = lastPulseAt;
  interrupts();
  return value;
}

void outputsOff() {
  digitalWrite(F_PIN, LOW);
  digitalWrite(R_PIN, LOW);
  digitalWrite(LED_BUILTIN, LOW);
}

void reply(unsigned long id, bool success, float actual, const char *reason) {
  // D,id,success,actual_mm,position_mm,reference_valid,pulses,reason
  noInterrupts();
  unsigned long count = pulses;
  bool valid = referenced;
  interrupts();
  Serial.print("D,"); Serial.print(id);
  Serial.print(','); Serial.print(success ? 1 : 0);
  Serial.print(','); Serial.print(actual, 3);
  Serial.print(','); Serial.print(positionMm(), 3);
  Serial.print(','); Serial.print(valid ? 1 : 0);
  Serial.print(','); Serial.print(count);
  Serial.print(','); Serial.println(reason);
}

void finishMovement(bool success, const char *reason) {
  outputsOff();
  if (state == MOVING) {
    state = SETTLING;
    stoppedAt = millis();
    resultSuccess = success;
    resultReason = reason;
  } else if (state == SETTLING && !success) {
    resultSuccess = false;
    resultReason = reason;
  }
}

void handleLine(const char *line) {
  unsigned long id;
  float distance, maximum, step;
  char extra;
  if (!strcmp(line, "K")) {
    lastHeartbeat = millis();
  } else if (!strcmp(line, "S")) {
    finishMovement(false, "CANCELLED");
  } else if (!strcmp(line, "Q")) {
    Serial.println("HELLO,ARM_EXTENSION_V1");
  } else if (sscanf(line, "C,%f,%f%c", &maximum, &step, &extra) == 2) {
    if (state == IDLE && isfinite(maximum) && isfinite(step) && maximum > 0 && step > 0) {
      maxPosition = maximum; maxMove = step;
      Serial.println("CONFIG_OK");
    } else Serial.println("CONFIG_REJECTED");
  } else if (sscanf(line, "Z,%lu%c", &id, &extra) == 1) {
    // 配線断線と押下は電気的に同じ。原点実物は人が確認する。
    if (state != IDLE || millis() < REST_MS ||
        millis() - lastPulseTime() < 1000 || !homeActive || digitalRead(HOME_PIN) != HIGH) {
      reply(id, false, 0, "ZERO_REJECTED_WAIT_AND_CHECK_HOME");
      return;
    }
    noInterrupts();
    steps = 0; direction = 0; referenced = true;
    interrupts();
    reply(id, true, 0, "ZERO_OK");
  } else if (sscanf(line, "H,%lu%c", &id, &extra) == 1) {
    // 原点復帰: F方向へ進み、NC原点スイッチが押されたら減速停止する。
    // スイッチ断線も「押下」と同じHIGHになるため、開始前に実物が未押下か確認する。
    if (state != IDLE) { reply(id, false, 0, "BUSY"); return; }
    if (maxPosition <= 0 || maxMove <= 0) {
      reply(id, false, 0, "NOT_CONFIGURED"); return;
    }
    if (homeActive) {
      noInterrupts();
      steps = 0; direction = 0; referenced = true;
      interrupts();
      reply(id, true, 0, "HOME_ALREADY_ACTIVE_ZEROED");
      return;
    }
    outputsOff();
    activeId = id; requested = 0; startPosition = 0;
    direction = -1; homing = true;
    startedAt = lastHeartbeat = millis();
    state = MOVING;
    digitalWrite(F_PIN, HIGH);
    digitalWrite(LED_BUILTIN, HIGH);
  } else if (sscanf(line, "M,%lu,%f%c", &id, &distance, &extra) == 2) {
    if (state != IDLE) { reply(id, false, 0, "BUSY"); return; }
    if (!referenced) { reply(id, false, 0, "NOT_REFERENCED"); return; }
    if (!isfinite(distance) || distance == 0 || fabsf(distance) > maxMove || maxPosition <= 0) {
      reply(id, false, 0, "INVALID_DISTANCE_OR_NOT_CONFIGURED"); return;
    }
    float current = positionMm(), target = current + distance;
    if (target < 0 || target > maxPosition) { reply(id, false, 0, "OUT_OF_RANGE"); return; }
    if (distance < 0 && homeActive) { reply(id, false, 0, "HOME_LIMIT"); return; }
    outputsOff();
    activeId = id; requested = distance; startPosition = current; homing = false;
    direction = distance > 0 ? 1 : -1;
    startedAt = lastHeartbeat = millis();
    state = MOVING;
    digitalWrite(distance > 0 ? R_PIN : F_PIN, HIGH);
    digitalWrite(LED_BUILTIN, HIGH);
  } else {
    finishMovement(false, "BAD_COMMAND");
  }
}

void setup() {
  digitalWrite(F_PIN, LOW); digitalWrite(R_PIN, LOW);
  pinMode(F_PIN, OUTPUT); pinMode(R_PIN, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT); outputsOff();
  pinMode(HOME_PIN, INPUT_PULLUP);
  pinMode(SPEED_PIN, INPUT); // 外部10kΩで3.3Vへプルアップ済み。
  Serial.begin(115200);
  attachInterrupt(digitalPinToInterrupt(SPEED_PIN), countPulse, RISING);
}

void loop() {
  unsigned long now = millis();
  bool homeOpen = digitalRead(HOME_PIN) == HIGH;
  if (homeOpen) {
    homeActive = true; homeClosedAt = now;
  } else {
    if (lastHomeOpen) homeClosedAt = now;
    if (now - homeClosedAt >= 50) homeActive = false;
  }
  lastHomeOpen = homeOpen;

  // USBの受信を待たずに、毎ループ停止条件を確認する。
  if (state == MOVING) {
    float travelled = positionMm() - startPosition;
    unsigned long lastPulse = lastPulseTime();
    if (homing && homeActive) finishMovement(true, "HOME_SWITCH");
    else if (direction < 0 && homeActive) finishMovement(false, "HOME_LIMIT");
    else if (!homing && !referenced) finishMovement(false, "POSITION_INVALID");
    else if (now - lastHeartbeat >= WATCHDOG_MS) finishMovement(false, "USB_TIMEOUT");
    else if (now - startedAt >= RUN_TIMEOUT_MS) finishMovement(false, "RUN_TIMEOUT");
    else if (now - startedAt >= STALL_MS && now - lastPulse >= STALL_MS) {
      referenced = false;
      finishMovement(false, "NO_PULSES_CHECK_SPEED_WIRING");
    } else if (!homing && fabsf(travelled) >= fabsf(requested)) finishMovement(true, "TARGET_STOP_COMMAND");
  }
  if (state == SETTLING && now - stoppedAt >= REST_MS) {
    bool stillMoving = now - lastPulseTime() < 1000;
    if (homing && resultSuccess && homeActive && !stillMoving) {
      noInterrupts();
      steps = 0; direction = 0; referenced = true;
      interrupts();
      resultReason = "HOME_OK";
    } else if (stillMoving || positionMm() < -MM_PER_PULSE || positionMm() > maxPosition) {
      referenced = false;
      resultSuccess = false;
      resultReason = stillMoving ? "STILL_MOVING_CHECK_HARDWARE" : "OVERRUN_CHECK_TRAVEL_RANGE";
    }
    reply(activeId, resultSuccess, positionMm() - startPosition, resultReason);
    state = IDLE; homing = false; // 減速中も元の方向で数え、10秒後の推定値を返す。
  }

  // 1ループの受信処理量を制限し、停止条件の確認を妨げない。
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (!discardLine && used) { buffer[used] = 0; handleLine(buffer); }
      used = 0; discardLine = false;
    } else if (used < sizeof(buffer) - 1 && !discardLine) buffer[used++] = c;
    else { discardLine = true; finishMovement(false, "COMMAND_TOO_LONG"); }
  }
}
