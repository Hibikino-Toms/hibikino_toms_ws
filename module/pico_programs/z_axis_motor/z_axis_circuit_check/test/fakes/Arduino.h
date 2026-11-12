#pragma once
#include <deque>
#include <sstream>
#include <string>
#define LOW 0
#define HIGH 1
#define INPUT_PULLUP 2
#define OUTPUT 3
inline int levels[32] = {};
inline unsigned long clockMs = 0;
inline unsigned long millis() { return clockMs; }
inline void pinMode(int pin, int mode) { if (mode == INPUT_PULLUP) levels[pin] = HIGH; }
inline void digitalWrite(int pin, int value) { levels[pin] = value; }
inline int digitalRead(int pin) { return levels[pin]; }
struct FakeSerial {
  bool connected = true;
  std::deque<char> input;
  std::ostringstream output;
  void begin(int) {}
  explicit operator bool() const { return connected; }
  int available() { return static_cast<int>(input.size()); }
  int read() { const char c = input.front(); input.pop_front(); return c; }
  template <typename T> void print(T v) { output << v; }
  template <typename T> void println(T v) { output << v << '\n'; }
  void send(const std::string &s) { for (char c : s) input.push_back(c); }
};
inline FakeSerial Serial;
