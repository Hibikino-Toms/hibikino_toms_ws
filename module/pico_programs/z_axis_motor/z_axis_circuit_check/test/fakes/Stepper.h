#pragma once
#include "Arduino.h"
inline int downSteps = 0;
inline int upSteps = 0;
inline int tripAtStep = -1;
class Stepper {
  int firstPin;
 public:
  Stepper(int, int pin, int) : firstPin(pin) {}
  void setSpeed(long) {}
  void step(int count) {
    clockMs += count;
    if (firstPin == 16) {
      downSteps += count;
      if (tripAtStep >= 0 && downSteps >= tripAtStep) levels[26] = LOW;
    } else { upSteps += count; }
  }
};
