// Compile the actual sketch against fake GPIO/clock/USB. Never opens hardware.
#include <cassert>
#include <iostream>
#include "../z_axis_tracking.ino"

void reset() {
  phase=IDLE;positionSteps=targetSteps=homeTravel=0;
  commandId=lastHost=lastStatus=motionStart=lastStepUs=lastRampUs=0;
  maxSpeed=10;speed=0;homed=false;powered=true;modern=false;legacyReply=0;
  fault="NONE";lineLength=0;lineOverflow=false;clockMs=0;
  downSteps=upSteps=0;tripAtStep=-1;
  Serial.connected=true;Serial.txAvailable=512;Serial.input.clear();Serial.output.str("");Serial.output.clear();
  setup();
}
void tick(unsigned ms=1, bool heartbeat=true) {
  clockMs+=ms;
  if(heartbeat && modern && clockMs-lastHost>=100)parse("ZINFO");
  loop();
}
void run(unsigned milliseconds, bool heartbeat=true) {
  const auto end=clockMs+milliseconds;
  while(clockMs<end)tick(1, heartbeat);
}
void calibrated(long mm=225) { homed=true;positionSteps=mm*STEPS_PER_MM;parse("ZINFO"); }
bool faultIs(const char *value){return strcmp(fault,value)==0;}

int main() {
  reset();calibrated(5);parse("ZMOVE,201,5,10.000");
  assert(!moving() && commandId==201 && faultIs("NONE"));
  assert(Serial.output.str().find("ZERR")==std::string::npos);
  parse("ZMOVE,202,10,10.000");assert(moving() && maxSpeed==10.f);
  parse("ZSTOP");
  parse("ZMOVE,203,10,10.000junk");assert(!moving());
  assert(Serial.output.str().find("MALFORMED_SPEED")!=std::string::npos);
  parse("ZMOVE,204,10,nan");assert(!moving());
  parse("ZMOVE,205,10,20.001");assert(!moving());

  reset();run(1000);
  assert(downSteps==0 && upSteps==0 && !homed && levels[AWO]==LOW);
  parse("ZMOVE,1,230,10");assert(!moving() && !homed);
  assert(Serial.output.str().find("NOT_HOMED")!=std::string::npos);

  reset();parse("ZINFO");tripAtStep=10;parse("ZHOME,1");
  for(int i=0;i<10000 && moving();++i){
    if(phase==HOME_BACKOFF && positionSteps>10)levels[LIMIT_PIN]=HIGH;
    tick();
  }
  assert(homed && phase==IDLE && positionSteps==1000 && upSteps==1000 && downSteps==10);
  assert(faultIs("NONE") && levels[AWO]==LOW);
  assert(Serial.output.str().find("ZTRACK_V1,STATE,1000,1,0,1,0,1,NONE")!=std::string::npos);

  reset();calibrated();parse("ZMOVE,1,245,10");run(200);
  assert(moving() && upSteps>0 && positionSteps<245*200);
  long fixedTarget=targetSteps;parse("ZMOVE,2,210,10");
  assert(targetSteps==fixedTarget && commandId==1); // No queued/overwritten motion.
  parse("ZSTOP");auto pulses=upSteps+downSteps;run(300);
  assert(!moving() && upSteps+downSteps==pulses && levels[AWO]==LOW);

  reset();calibrated();parse("ZMOVE,1,235,10");run(5000);
  assert(!moving() && positionSteps==235*200 && homed && faultIs("NONE"));
  reset();calibrated();parse("ZMOVE,1,210,10");run(700, false);
  assert(!moving() && faultIs("HOST_TIMEOUT") && levels[AWO]==LOW);
  reset();calibrated();parse("ZMOVE,1,210,10");Serial.txAvailable=0;run(700,false);
  assert(!moving() && faultIs("HOST_TIMEOUT")); // Full USB TX cannot block checks.
  reset();calibrated();parse("ZMOVE,1,210,10");Serial.connected=false;tick();
  assert(!moving() && faultIs("USB_LOST"));

  reset();calibrated();levels[LIMIT_PIN]=LOW;parse("ZMOVE,1,210,10");
  assert(!moving() && downSteps==0);
  parse("ZMOVE,2,230,10");tick();assert(moving()); // Away from switch allowed.
  reset();calibrated();parse("ZMOVE,1,210,10");run(100);levels[LIMIT_PIN]=LOW;
  auto downBefore=downSteps;tick();assert(!moving() && downSteps==downBefore && faultIs("LIMIT_ACTIVE"));
  reset();levels[LIMIT_PIN]=LOW;parse("ZINFO");parse("ZHOME,1");run(5000);
  assert(!moving() && !homed && faultIs("LIMIT_STUCK_OR_WIRE_FAULT") && upSteps==400);
  reset();parse("ZINFO");parse("ZHOME,1");clockMs=HOME_TIMEOUT_MS+1;parse("ZINFO");loop();
  assert(!moving() && !homed && faultIs("MOTION_TIMEOUT"));

  reset();calibrated();parse("ZMOVE,1,451,10");assert(!moving());
  parse("ZMOVE,1,225,25");assert(!moving());
  Serial.output.str("");parse("3,226");run(2000);
  assert(!modern && !moving() && Serial.output.str()=="3 226\n");
  Serial.output.str("");parse("0,0");assert(!powered && levels[AWO]==HIGH);
  parse("1,0");assert(powered && levels[AWO]==LOW);
  assert(Serial.output.str()=="0 0\n1 0\n");
  std::cout<<"Z firmware native checks passed: boot, homing, limits, stop, watchdog, USB, no queue, legacy\n";
}
