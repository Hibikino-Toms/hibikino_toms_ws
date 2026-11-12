// Standalone Z-axis circuit check. No automatic motion and no ROS protocol.
// Measured installed circuit: GP26=HIGH when clear, LOW when pressed or disconnected.
#include <Arduino.h>
#include <Stepper.h>

constexpr int CW_A = 16;
constexpr int CW_B = 17;
constexpr int CCW_A = 18;
constexpr int CCW_B = 19;
constexpr int AWO = 20;                 // LOW enables holding power.
constexpr int LIMIT_PIN = 26;          // Installed interface: LOW = limit/fault active.
constexpr int STEPS_PER_REVOLUTION = 500;
constexpr int TEST_RPM = 120;          // Original sketch: 1000 RPM.
constexpr int JOG_STEPS = 200;         // Old conversion: approximately 1 mm.
constexpr int SEEK_MAX_STEPS = 2000;   // Approximately 10 mm; never full homing.
constexpr unsigned long MOTION_TIMEOUT_MS = 4000;
constexpr unsigned long STATUS_INTERVAL_MS = 250;

Stepper downMotor(STEPS_PER_REVOLUTION, CW_A, CW_B);
Stepper upMotor(STEPS_PER_REVOLUTION, CCW_A, CCW_B);
int motionDirection = 0;               // -1 = down/CW; +1 = up/CCW.
int requestedSteps = 0;
int completedSteps = 0;
bool powerEnabled = true;
bool connectedBefore = false;
unsigned long motionStartedMs = 0;
unsigned long lastStatusMs = 0;
const char *stopReason = "boot_hold_no_motion";

bool limitTripped() { return digitalRead(LIMIT_PIN) == LOW; }

void stopMotion(const char *reason) {
  motionDirection = 0;
  digitalWrite(CW_A, LOW);
  digitalWrite(CW_B, LOW);
  digitalWrite(CCW_A, LOW);
  digitalWrite(CCW_B, LOW);
  stopReason = reason;                 // Keep AWO unchanged: retain holding.
}

void printStatus() {
  Serial.print("Z_CHECK GP26=");
  Serial.print(digitalRead(LIMIT_PIN));
  Serial.print(limitTripped() ? " LIMIT=OPEN/TRIPPED" : " LIMIT=CLOSED/NC");
  Serial.print(" POWER="); Serial.print(powerEnabled ? "ON" : "OFF");
  Serial.print(" MOVE=");
  Serial.print(motionDirection < 0 ? "DOWN_CW" : motionDirection > 0 ? "UP_CCW" : "STOP");
  Serial.print(" STEPS="); Serial.print(completedSteps);
  Serial.print('/'); Serial.print(requestedSteps);
  Serial.print(" PINS16_19=");
  Serial.print(digitalRead(CW_A)); Serial.print(digitalRead(CW_B));
  Serial.print(digitalRead(CCW_A)); Serial.print(digitalRead(CCW_B));
  Serial.print(" AWO20="); Serial.print(digitalRead(AWO));
  Serial.print(" REASON="); Serial.println(stopReason);
}

void printHelp() {
  Serial.println("Z_AXIS_CIRCUIT_CHECK_V1: GP16/17=CW/down, GP18/19=CCW/up, GP20=AWO, GP26 active-low limit");
  Serial.println("GP26=HIGH clear; LOW=limit/fault. u=UP 200 steps; d=DOWN 200; t=DOWN until LOW (max 2000/4s)");
  Serial.println("x or Space=STOP/HOLD; e=enable holding; F=explicit POWER OFF (support the axis first)");
  Serial.println("p=status; ?=help. No absolute position/homing. ROS launch must remain stopped.");
}

void startMotion(int direction, int steps) {
  if (motionDirection != 0) return;     // No command queue.
  requestedSteps = steps;
  completedSteps = 0;
  if (!powerEnabled) { stopMotion("power_off_send_e_first"); return; }
  if (direction < 0 && limitTripped()) { stopMotion("down_blocked_limit_active"); return; }
  motionDirection = direction;
  motionStartedMs = millis();
  stopReason = "finite_manual_test";
}

void readCommands() {
  bool motionCommandSeen = false;
  bool stopSeen = false;
  // Coalesce an input burst: queued/repeated jogs cannot extend a movement.
  while (Serial.available() > 0) {
    const char key = static_cast<char>(Serial.read());
    if (key == 'x' || key == ' ' || key == 27 || key == 'F') {
      stopMotion("manual_stop");
      stopSeen = true;
      if (key == 'F') {
        powerEnabled = false;
        digitalWrite(AWO, HIGH);       // Only this explicit command removes power.
        stopReason = "manual_power_off";
      }
    } else if (key == 'e') {
      powerEnabled = true;
      digitalWrite(AWO, LOW);
    } else if (key == 'p') {
      printStatus();
    } else if (key == '?') {
      printHelp();
    } else if ((key == 'u' || key == 'd' || key == 't') && !stopSeen && !motionCommandSeen) {
      motionCommandSeen = true;
      startMotion(key == 'u' ? 1 : -1, key == 't' ? SEEK_MAX_STEPS : JOG_STEPS);
    }
  }
}

void setup() {
  // Hold the vertical mechanism; do not execute a power-off/on startup cycle.
  digitalWrite(AWO, LOW);
  pinMode(AWO, OUTPUT);
  pinMode(LIMIT_PIN, INPUT_PULLUP);
  stopMotion("boot_hold_no_motion");
  downMotor.setSpeed(TEST_RPM);
  upMotor.setSpeed(TEST_RPM);
  Serial.begin(115200);
}

void loop() {
  const bool connected = static_cast<bool>(Serial);
  if (connected && !connectedBefore) { printHelp(); printStatus(); }
  if (!connected && motionDirection != 0) stopMotion("USB_monitor_disconnected");
  connectedBefore = connected;
  if (connected) readCommands();
  if (motionDirection != 0) {
    if (millis() - motionStartedMs >= MOTION_TIMEOUT_MS) {
      stopMotion("motion_timeout");
    } else if (motionDirection < 0 && limitTripped()) {
      // Stop on the first active sample; no continued stepping during debounce.
      stopMotion("limit_active_stop");
    } else {
      if (motionDirection < 0) downMotor.step(1); else upMotor.step(1);
      ++completedSteps;
      if (motionDirection < 0 && limitTripped()) stopMotion("limit_active_stop");
      else if (completedSteps >= requestedSteps) stopMotion("step_budget_complete");
    }
  }
  if (connected && millis() - lastStatusMs >= STATUS_INTERVAL_MS) {
    lastStatusMs = millis();
    printStatus();
  }
}
