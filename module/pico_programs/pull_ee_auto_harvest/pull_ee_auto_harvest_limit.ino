// Pico 2 W: 2026-11 EE (roll DC + rail DC + continuous hook servo).
// Confirmed wiring: roll GP10/11 + ADC26, rail GP12/13 + encoder GP8/9,
// hook servo GP17 + ADC28, NC home limit GP19 to GND.
// Physical M commands: M1=roll, M2=rail, M3=hook (positive closes).
// DRIVE retains the ROS logical order [roll, unused pitch, hook, rail].
#include <Arduino.h>
#include <hardware/clocks.h>
#include <hardware/gpio.h>
#include <hardware/pwm.h>
#include <stdio.h>
#include <string.h>
#include "rail_homing.h"

constexpr uint8_t kRollIn1 = 10, kRollIn2 = 11;
constexpr uint8_t kRailIn1 = 12, kRailIn2 = 13;
constexpr uint8_t kRollAdc = 26, kHookAdc = 28;
constexpr uint8_t kEncoderA = 8, kEncoderB = 9;
constexpr uint8_t kServoPin = 17, kLimitPin = 19;
// Measured command endpoints from module/set_params.yaml (auto_harvest.hook_servo).
// Closing is above neutral; opening is below neutral on this installation.
constexpr int kServoNeutralUs = 1500, kServoCloseUs = 1600, kServoOpenUs = 1350;
constexpr int kServoMinUs = (kServoCloseUs < kServoOpenUs) ? kServoCloseUs : kServoOpenUs;
constexpr int kServoMaxUs = (kServoCloseUs > kServoOpenUs) ? kServoCloseUs : kServoOpenUs;
constexpr uint32_t kWatchdogMs = 600, kStatusMs = 100;
constexpr uint16_t kServoWrap = 59999;
volatile int32_t encoderRaw = 0;
volatile int8_t encoderQuarter = 0;
volatile uint8_t encoderState = 0;
const int8_t kTransitions[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
int encoderSign = 0;  // Learned from actual retract travel, not guessed.
int logicalDrive[4] = {0, 0, 0, 0};
int servoPulseUs = kServoNeutralUs;
float servoDivider = 1.0f;
uint32_t lastHostMs = 0, lastStatusMs = 0;
char commandBuffer[128];
size_t commandLength = 0;
bool discardCommand = false;
RailHoming home;

int32_t encoderSnapshot() {
  noInterrupts();
  const int32_t value = encoderRaw;
  interrupts();
  return value;
}
bool switchOpen() { return digitalRead(kLimitPin) == HIGH; }
void setDc(uint8_t in1, uint8_t in2, int pwm) {
  pwm = constrain(pwm, -255, 255);
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  if (pwm > 0) analogWrite(in1, pwm);
  if (pwm < 0) analogWrite(in2, -pwm);
}
void writeServo(int pulseUs) {
  // Endpoints may be ordered either way around neutral; constrain always
  // receives numeric lower/upper bounds.
  servoPulseUs = constrain(pulseUs, kServoMinUs, kServoMaxUs);
  const float clockHz = static_cast<float>(clock_get_hz(clk_sys)) / servoDivider;
  pwm_set_gpio_level(kServoPin, static_cast<uint16_t>(clockHz * servoPulseUs / 1000000.0f));
}
void applyOutputs(int roll, int hook, int rail) {
  // Raw NC opening blocks only further retraction, not motion away from home.
  if (switchOpen() && rail > 0) rail = 0;
  logicalDrive[0] = constrain(roll, -255, 255);
  logicalDrive[1] = 0;
  logicalDrive[2] = constrain(hook, -255, 255);
  logicalDrive[3] = constrain(rail, -255, 255);
  setDc(kRollIn1, kRollIn2, logicalDrive[0]);
  // Keep the ROS/EEPROM logical direction as +retract, -extend. The
  // installed rail motor runs opposite to the previous GP12/GP13 assumption,
  // so logical + must drive IN2 (GP13), and logical - must drive IN1 (GP12).
  setDc(kRailIn2, kRailIn1, logicalDrive[3]);
  const int hookPwm = logicalDrive[2];
  const int endUs = hookPwm >= 0 ? kServoCloseUs : kServoOpenUs;
  writeServo(kServoNeutralUs + (endUs-kServoNeutralUs)*abs(hookPwm)/255);
}
void stopOutputs() { applyOutputs(0, 0, 0); }
void stopSession(const char *reason) { home.cancel(reason); stopOutputs(); }
bool outputsStopped() {
  return logicalDrive[0] == 0 && logicalDrive[2] == 0 && logicalDrive[3] == 0;
}
void updateEncoder() {
  const uint8_t now = (digitalRead(kEncoderA) << 1) | digitalRead(kEncoderB);
  encoderQuarter += kTransitions[(encoderState << 2) | now];
  encoderState = now;
  if (encoderQuarter >= 4) { ++encoderRaw; encoderQuarter = 0; }
  if (encoderQuarter <= -4) { --encoderRaw; encoderQuarter = 0; }
}
void updateHome() {
  if (!home.active()) return;
  const int32_t raw = encoderSnapshot();
  home.update(millis(), raw, switchOpen());
  if (home.phase() == RailHoming::DONE) {
    encoderSign = home.retractEncoderSign(raw);
    if (encoderSign == 0) {
      home.invalidate("NO_ENCODER_REFERENCE_TRAVEL");
    } else {
      // The debounced retract switch is the only source of an encoder zero.
      noInterrupts();
      encoderRaw = 0;
      encoderQuarter = 0;
      encoderState = (digitalRead(kEncoderA) << 1) | digitalRead(kEncoderB);
      interrupts();
    }
  }
  applyOutputs(0, 0, home.outputPwm());
}
void reject(const char *reason) {
  stopSession(reason);
  Serial.print("[ERROR] "); Serial.println(reason);
}
void command(const char *line) {
  if (strcmp(line, "STOP") == 0) { stopSession("STOP"); lastHostMs = millis(); return; }
  if (strcmp(line, "KEEPALIVE") == 0) { lastHostMs = millis(); return; }
  unsigned long id = 0, timeout = 0, debounce = 0, release = 0, travel = 0, progress = 0;
  int pwm = 0;
  char extra;
  if (sscanf(line, "HOME_ENC4 %lu,%d,%lu,%lu,%lu,%lu,%lu%c",
             &id, &pwm, &timeout, &debounce, &release, &travel, &progress, &extra) == 7) {
    if (id != 0 && id == home.id()) { lastHostMs = millis(); return; }
    if (home.active() || !outputsStopped() || id == 0 || id > 2000000000UL || pwm < 1 || pwm > 255 ||
        timeout < 1000 || timeout > 60000 || debounce < 5 || debounce > 500 ||
        release < 1 || release > 50 || travel < 1 || travel > 100000 ||
        progress < 100 || progress > timeout) return reject("BAD_HOME_REQUEST");
    encoderSign = 0;
    const RailHoming::Config cfg = {pwm, static_cast<uint32_t>(timeout), static_cast<uint32_t>(debounce),
        static_cast<uint32_t>(release), static_cast<uint32_t>(travel), static_cast<uint32_t>(progress)};
    home.start(id, cfg, millis(), encoderSnapshot(), switchOpen());
    lastHostMs = millis();
    applyOutputs(0, 0, home.outputPwm());
    return;
  }
  if (home.active()) return reject("HOME_OWNS_OUTPUTS");
  if (strcmp(line, "ZERO_ENC4") == 0) return reject("ZERO_REQUIRES_SWITCH_HOMING");
  int drive[4];
  if (sscanf(line, "DRIVE %d,%d,%d,%d%c", &drive[0], &drive[1],
             &drive[2], &drive[3], &extra) == 4) {
    if (drive[1] != 0) return reject("NO_PITCH_AXIS");
    applyOutputs(drive[0], drive[2], drive[3]);
    lastHostMs = millis();
    return;
  }
  int motor = 0;
  if (sscanf(line, "M%d,%d%c", &motor, &pwm, &extra) == 2 && motor >= 1 && motor <= 3) {
    applyOutputs(motor == 1 ? pwm : 0, motor == 3 ? pwm : 0, motor == 2 ? pwm : 0);
    lastHostMs = millis();
    return;
  }
  reject("BAD_COMMAND");
}
void receiveCommands() {
  // Bound work per loop so serial traffic cannot starve the switch/watchdog.
  for (uint8_t i=0; i<64 && Serial.available(); ++i) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      if (!discardCommand && commandLength) {
        commandBuffer[commandLength] = '\0'; command(commandBuffer);
      }
      commandLength = 0; discardCommand = false;
    } else if (!discardCommand && commandLength < sizeof(commandBuffer)-1) {
      commandBuffer[commandLength++] = c;
    } else {
      discardCommand = true;
      reject("COMMAND_OVERFLOW");
    }
  }
}
void printStatus() {
  char line[256];
  const int size = snprintf(line, sizeof(line),
      "[STATUS] PWM=%d,%d,%d,%d ENC4=%ld POT1=%u,raw SERVO_FB=%u,raw "
      "SERVO_US=%d LIMIT=%d HOME_CAP=1 PROFILE=ROLL_RAIL_SERVO_V1 "
      "HOME=%s HOME_ID=%lu HOME_ERROR=%s ENC_SIGN=%d\n",
      logicalDrive[0], logicalDrive[1], logicalDrive[2], logicalDrive[3],
      static_cast<long>(encoderSnapshot() * (encoderSign ? encoderSign : 1)),
      static_cast<unsigned>(analogRead(kRollAdc)), static_cast<unsigned>(analogRead(kHookAdc)),
      servoPulseUs, switchOpen() ? 1 : 0, home.phaseName(),
      static_cast<unsigned long>(home.id()), home.error(), encoderSign);
  // Do not block switch handling or the watchdog on a stalled USB host.
  if (size > 0 && size < static_cast<int>(sizeof(line)) && Serial.availableForWrite() >= size)
    Serial.write(reinterpret_cast<const uint8_t *>(line), static_cast<size_t>(size));
}
void setup() {
  Serial.begin(115200);
  analogWriteRange(255); analogWriteFreq(20000); analogReadResolution(12);
  const uint8_t dcPins[] = {kRollIn1, kRollIn2, kRailIn1, kRailIn2};
  for (uint8_t p : dcPins) pinMode(p, OUTPUT);
  pinMode(kRollAdc, INPUT); pinMode(kHookAdc, INPUT);
  pinMode(kLimitPin, INPUT_PULLUP);
  pinMode(kEncoderA, INPUT_PULLUP); pinMode(kEncoderB, INPUT_PULLUP);
  encoderState = (digitalRead(kEncoderA) << 1) | digitalRead(kEncoderB);
  attachInterrupt(digitalPinToInterrupt(kEncoderA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(kEncoderB), updateEncoder, CHANGE);
  gpio_set_function(kServoPin, GPIO_FUNC_PWM);
  servoDivider = static_cast<float>(clock_get_hz(clk_sys)) / (50.0f*(kServoWrap+1.0f));
  pwm_config cfg = pwm_get_default_config();
  pwm_config_set_clkdiv(&cfg, servoDivider); pwm_config_set_wrap(&cfg, kServoWrap);
  const uint slice = pwm_gpio_to_slice_num(kServoPin);
  pwm_init(slice, &cfg, false); stopOutputs(); pwm_set_enabled(slice, true);
  lastHostMs = millis();
  Serial.println("[READY] ROLL_RAIL_SERVO_V1 STOPPED LIMIT_GP19 HOME_COMMAND_REQUIRED");
}
void loop() {
  updateHome();
  if (switchOpen() && logicalDrive[3] > 0) applyOutputs(logicalDrive[0], logicalDrive[2], 0);
  if ((home.active() || !outputsStopped()) && millis()-lastHostMs > kWatchdogMs)
    stopSession("HOST_TIMEOUT");
  receiveCommands();
  if (millis()-lastStatusMs >= kStatusMs) { lastStatusMs = millis(); printStatus(); }
  delay(1);
}
