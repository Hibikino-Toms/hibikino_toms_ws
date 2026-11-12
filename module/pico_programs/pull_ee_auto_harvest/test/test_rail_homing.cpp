// Native checks of the exact state machine compiled into the Pico sketch.
#include "../rail_homing.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main() {
  RailHoming h;
  const RailHoming::Config cfg = {140, 20000, 40, 4, 70, 3000};
  h.start(1, cfg, 0, 10, false);
  assert(h.outputPwm() == 140);
  h.update(10, 11, true);
  assert(h.phase() == RailHoming::CONTACT && h.outputPwm() == 0);
  h.update(49, 11, true);
  assert(h.phase() == RailHoming::CONTACT);
  h.update(50, 11, true);
  assert(h.phase() == RailHoming::DONE && h.retractEncoderSign(11) == 1);

  // Bounce stops immediately and does not establish zero prematurely.
  h.start(2, cfg, 0, 0, false);
  h.update(10, -1, true);
  h.update(20, -1, false);
  assert(h.phase() == RailHoming::SEEK && h.outputPwm() == 140);
  h.update(30, -2, true);
  h.update(69, -2, true);
  assert(h.phase() != RailHoming::DONE);
  h.update(70, -2, true);
  assert(h.phase() == RailHoming::DONE && h.retractEncoderSign(-2) == -1);

  // An open switch at startup is not home: require close, then reopen.
  h.start(3, cfg, 0, 5, true);
  assert(h.phase() == RailHoming::RELEASE && h.outputPwm() == -140);
  h.update(10, 4, false);
  assert(h.outputPwm() == 0);
  h.update(50, 4, false);
  assert(h.phase() == RailHoming::SEEK && h.outputPwm() == 140);
  h.update(60, 5, true);
  h.update(100, 5, true);
  assert(h.phase() == RailHoming::DONE);

  h.start(10, cfg, 0, 0, false);
  h.update(10, 0, true);  // Home switch reached before any encoder detent.
  h.update(50, 0, true);
  assert(h.phase() == RailHoming::RELEASE);
  h.update(60, 0, false);
  assert(h.outputPwm() == -140);  // Must see at least one count while clearing.
  h.update(70, -1, false);
  assert(h.outputPwm() == 0);
  h.update(110, -1, false);
  h.update(120, 0, true);
  h.update(160, 0, true);
  assert(h.phase() == RailHoming::DONE && h.retractEncoderSign(0) == 1);

  h.start(4, cfg, 0, 0, true);
  h.update(10, -5, true);
  assert(h.phase() == RailHoming::FAULT && h.outputPwm() == 0);
  h.start(5, cfg, 0, 0, false);
  h.update(10, 71, false);
  assert(h.phase() == RailHoming::FAULT && h.outputPwm() == 0);
  h.start(6, cfg, 0, 0, false);
  h.update(3000, 0, false);
  assert(h.phase() == RailHoming::FAULT && h.outputPwm() == 0);
  h.start(7, cfg, 0, 0, false);
  h.update(20000, 1, false);
  assert(h.phase() == RailHoming::FAULT && h.outputPwm() == 0);
  h.start(8, cfg, 0, 0, false);
  h.cancel("HOST_TIMEOUT");
  h.update(10, 1, true);
  assert(h.phase() == RailHoming::CANCELLED && h.outputPwm() == 0);

  // Unsigned elapsed time survives the millis() wrap.
  h.start(9, cfg, UINT32_MAX-10, 0, false);
  h.update(5, 1, true);
  h.update(45, 1, true);
  assert(h.phase() == RailHoming::DONE);
  puts("Pico homing state machine: all native safety checks passed");
}
