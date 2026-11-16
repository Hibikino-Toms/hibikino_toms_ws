#pragma once
// Match only the Arduino API used by this sketch; all hardware is in memory.
#include <deque>
#include <sstream>
#include <string>
#define LOW 0
#define HIGH 1
#define INPUT_PULLUP 2
#define OUTPUT 3
inline int levels[32] = {};
inline unsigned long clockMs=0;
inline unsigned long millis(){return clockMs;}
inline void pinMode(int pin,int mode){if(mode==INPUT_PULLUP)levels[pin]=HIGH;}
inline void digitalWrite(int pin,int level){levels[pin]=level;}
inline int digitalRead(int pin){return levels[pin];}
struct FakeSerial {
  bool connected=true;
  int txAvailable=512;
  std::deque<char> input;
  std::ostringstream output;
  void begin(int){}
  explicit operator bool() const{return connected;}
  int available(){return static_cast<int>(input.size());}
  int availableForWrite(){return txAvailable;}
  int read(){char c=input.front();input.pop_front();return c;}
  template<typename T>void print(T value){output<<value;}
  template<typename T>void println(T value){output<<value<<'\n';}
};
inline FakeSerial Serial;
#include <algorithm>
#include <cstdlib>
using std::min;
using std::max;
inline unsigned long micros() { return clockMs*1000UL; }
