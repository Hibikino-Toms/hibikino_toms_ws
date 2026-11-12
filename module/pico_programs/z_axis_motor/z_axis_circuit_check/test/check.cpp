#include <cassert>
#include <cstring>
#include <iostream>
#include "../z_axis_circuit_check.ino"

void resetCheck() {
  Serial.connected = true;
  Serial.input.clear(); Serial.output.str("");
  clockMs = 0; downSteps = upSteps = 0; tripAtStep = -1;
  powerEnabled = true; connectedBefore = false;
  requestedSteps = completedSteps = 0;
  setup();
  levels[LIMIT_PIN] = HIGH; // Measured installed circuit: clear state is HIGH.
}
void finish() {
  for (int i = 0; i < 2200 && motionDirection != 0; ++i) loop();
  assert(motionDirection == 0);
  assert(levels[CW_A] == LOW && levels[CW_B] == LOW);
  assert(levels[CCW_A] == LOW && levels[CCW_B] == LOW);
  assert(levels[AWO] == LOW);
}
int main() {
  resetCheck(); for (int i = 0; i < 10; ++i) loop();
  assert(downSteps == 0 && upSteps == 0 && powerEnabled);
  Serial.send("p?\n2,0\n3,100\n"); loop();
  assert(downSteps == 0 && upSteps == 0);

  resetCheck(); levels[LIMIT_PIN] = LOW; // Pressed or disconnected: fail-safe active.
  Serial.send("d"); loop(); assert(downSteps == 0 && motionDirection == 0);
  Serial.send("u"); loop(); finish(); assert(upSteps == JOG_STEPS);

  resetCheck(); tripAtStep = 7;
  Serial.send("t"); loop(); finish();
  assert(downSteps == 7 && std::strcmp(stopReason, "limit_active_stop") == 0);
  Serial.send("d"); loop(); assert(downSteps == 7);

  resetCheck(); Serial.send("t"); loop(); finish();
  assert(downSteps == SEEK_MAX_STEPS);
  assert(std::strcmp(stopReason, "step_budget_complete") == 0);

  resetCheck(); Serial.send("uuuuuu"); loop(); finish();
  assert(upSteps == JOG_STEPS && Serial.available() == 0);

  resetCheck(); Serial.send("t"); loop();
  clockMs += MOTION_TIMEOUT_MS; loop();
  assert(motionDirection == 0 && downSteps == 1);
  assert(std::strcmp(stopReason, "motion_timeout") == 0);

  resetCheck(); Serial.send("t"); loop();
  Serial.send("xudt"); loop(); assert(motionDirection == 0 && downSteps == 1);

  resetCheck(); Serial.send("t"); loop();
  Serial.connected = false; loop();
  assert(motionDirection == 0 && levels[AWO] == LOW);

  resetCheck(); Serial.send("F"); loop();
  assert(!powerEnabled && levels[AWO] == HIGH);
  Serial.send("u"); loop(); assert(upSteps == 0);
  Serial.send("e"); loop(); assert(powerEnabled && motionDirection == 0);
  std::cout << "Z circuit check: boot, NC stop, release direction, travel/time limits, stop priority, disconnect and power controls passed\n";
}
