// Z-axis tracking firmware. Boot holds power but never moves or homes.
// GP26 measured circuit: HIGH=clear, LOW=pressed/disconnected.
#include <Arduino.h>
#include <Stepper.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

constexpr int CW_A=16, CW_B=17, CCW_A=18, CCW_B=19, AWO=20, LIMIT_PIN=26;
constexpr long STEPS_PER_MM=200;  // Existing conversion; verify on mechanism.
constexpr long MAX_STEPS=450*STEPS_PER_MM;
constexpr long HOME_RELEASE_STEPS=2*STEPS_PER_MM;
constexpr long HOME_BACKOFF_STEPS=5*STEPS_PER_MM;
constexpr unsigned long HOST_TIMEOUT_MS=600, STATUS_MS=100, HOME_TIMEOUT_MS=120000;
constexpr float ACCEL_MM_S2=20.f;
Stepper downMotor(500,CW_A,CW_B), upMotor(500,CCW_A,CCW_B);
enum Phase {IDLE, MOVE, HOME_RELEASE, HOME_SEEK, HOME_BACKOFF};
Phase phase=IDLE;
long positionSteps=0, targetSteps=0, homeTravel=0;
unsigned long commandId=0, lastHost=0, lastStatus=0, motionStart=0, lastStepUs=0, lastRampUs=0;
float maxSpeed=10.f, speed=0.f;
bool homed=false, powered=true, modern=false;
int legacyReply=0;
const char *fault="NONE";
char inputLine[96];
size_t lineLength=0;
bool lineOverflow=false;

bool limitActive(){return digitalRead(LIMIT_PIN)==LOW;}
bool moving(){return phase!=IDLE;}
void pulsesOff(){
  digitalWrite(CW_A,LOW);digitalWrite(CW_B,LOW);
  digitalWrite(CCW_A,LOW);digitalWrite(CCW_B,LOW);
}
void stopMotion(const char *why){
  if(phase==HOME_RELEASE || phase==HOME_SEEK || phase==HOME_BACKOFF) homed=false;
  phase=IDLE;speed=0.f;pulsesOff();fault=why;
  // AWO remains unchanged. No automatic torque/power OFF on fault or stop.
}
void state(){
  char line[160];
  int length=snprintf(line,sizeof(line),"ZTRACK_V1,STATE,%ld,%d,%d,%d,%d,%lu,%s\n",
      positionSteps,homed?1:0,moving()?1:0,powered?1:0,limitActive()?1:0,commandId,fault);
  // Drop telemetry if the host stops reading; never block limit/watchdog work
  // waiting for a full USB TX buffer to drain.
  if(length>0 && length<static_cast<int>(sizeof(line)) && Serial.availableForWrite()>=length)Serial.print(line);
}
void reject(const char *reason){
  if(Serial.availableForWrite()>=static_cast<int>(strlen(reason))+6){
    Serial.print("ZERR,");Serial.println(reason);
  }
}
void finish(){
  phase=IDLE;speed=0.f;pulsesOff();fault="NONE";
  if(legacyReply){
    Serial.print(legacyReply);Serial.print(' ');Serial.println(positionSteps/STEPS_PER_MM);
    legacyReply=0;
  }
  if(modern)state();
}
bool beginMove(long mm,float speedMmS,unsigned long id){
  if(moving()){reject("BUSY_NO_QUEUE");return false;}
  if(!homed){reject("NOT_HOMED");return false;}
  if(!powered){reject("POWER_OFF");return false;}
  if(!isfinite(speedMmS)||speedMmS<=0.f||speedMmS>20.f||mm<0||mm>450){reject("RANGE_OR_SPEED");return false;}
  if(mm*STEPS_PER_MM<positionSteps && limitActive()){reject("LIMIT_DOWN_BLOCKED");return false;}
  targetSteps=mm*STEPS_PER_MM;maxSpeed=speedMmS;speed=0.f;
  commandId=id;fault="NONE";motionStart=millis();lastStepUs=lastRampUs=micros();
  if(targetSteps==positionSteps){finish();return true;}
  phase=MOVE;
  return true;
}
bool beginHome(unsigned long id){
  if(moving()){reject("BUSY_NO_QUEUE");return false;}
  if(!powered){reject("POWER_OFF");return false;}
  homed=false;commandId=id;fault="NONE";speed=0.f;maxSpeed=5.f;
  homeTravel=0;motionStart=millis();lastStepUs=lastRampUs=micros();
  phase=limitActive()?HOME_RELEASE:HOME_SEEK;
  return true;
}
void parse(const char *line){
  unsigned long id=0;long mm=0;char tail;char rateText[32];
  if(strcmp(line,"ZINFO")==0){modern=true;lastHost=millis();state();return;}
  if(strcmp(line,"ZSTOP")==0){modern=true;lastHost=millis();stopMotion("NONE");state();return;}
  // The Pico's small C library can count a %f conversion without populating
  // the float. Parse the token with strtod instead of float scanf support.
  if(sscanf(line,"ZMOVE,%lu,%ld,%31s%c",&id,&mm,rateText,&tail)==3){
    char *end=nullptr;
    double rate=strtod(rateText,&end);
    if(end==rateText || *end!='\0'){reject("MALFORMED_SPEED");return;}
    modern=true;lastHost=millis();if(beginMove(mm,static_cast<float>(rate),id))state();return;
  }
  if(sscanf(line,"ZHOME,%lu%c",&id,&tail)==1){
    modern=true;lastHost=millis();if(beginHome(id))state();return;
  }
  // Legacy 0/1/2/3 commands remain available for the old service path.
  // Legacy completion replies only; it does not send heartbeat/status packets.
  int mode=-1;
  if(sscanf(line,"%d,%ld%c",&mode,&mm,&tail)==2){
    if(moving()){reject("BUSY_NO_QUEUE");return;}
    modern=false;
    if(mode==0){stopMotion("NONE");powered=false;digitalWrite(AWO,HIGH);Serial.println("0 0");}
    else if(mode==1){powered=true;digitalWrite(AWO,LOW);Serial.println("1 0");}
    else if(mode==2){legacyReply=2;if(!beginHome(++commandId))legacyReply=0;}
    else if(mode==3){legacyReply=3;if(!beginMove(mm,10.f,++commandId))legacyReply=0;}
    else Serial.println("5 -1");
    return;
  }
  reject("UNKNOWN_PROTOCOL_EXPECT_ZINFO");
}
void readCommands(){
  // Bound each pass so serial bursts cannot starve limit/watchdog checks.
  for(int n=0;n<192 && Serial.available()>0;++n){
    char c=static_cast<char>(Serial.read());
    if(c=='\r')continue;
    if(c=='\n'){
      if(lineOverflow)reject("LINE_OVERFLOW");
      else {inputLine[lineLength]='\0';parse(inputLine);}
      lineLength=0;lineOverflow=false;
    }else if(lineLength+1<sizeof(inputLine)) inputLine[lineLength++]=c;
    else lineOverflow=true;
  }
}
void motionTick(){
  if(!moving())return;
  if(!Serial){stopMotion("USB_LOST");return;}
  if(modern && millis()-lastHost>HOST_TIMEOUT_MS){stopMotion("HOST_TIMEOUT");return;}
  unsigned long timeout=phase==MOVE?60000:HOME_TIMEOUT_MS;
  if(millis()-motionStart>timeout){stopMotion("MOTION_TIMEOUT");return;}
  if(phase==HOME_RELEASE){
    if(!limitActive()){phase=HOME_SEEK;homeTravel=0;speed=0.f;}
    else if(homeTravel>=HOME_RELEASE_STEPS){stopMotion("LIMIT_STUCK_OR_WIRE_FAULT");return;}
  }
  if(phase==HOME_SEEK){
    if(limitActive()){
      pulsesOff();positionSteps=0;targetSteps=HOME_BACKOFF_STEPS;
      phase=HOME_BACKOFF;speed=0.f;homeTravel=0;
    }else if(homeTravel>=MAX_STEPS){stopMotion("HOME_TRAVEL_LIMIT");return;}
  }
  if(phase==HOME_BACKOFF && positionSteps>=targetSteps){
    if(limitActive()){stopMotion("LIMIT_DID_NOT_RELEASE");return;}
    homed=true;finish();return;
  }
  if(phase==MOVE && positionSteps==targetSteps){finish();return;}
  int direction=(phase==HOME_SEEK || (phase==MOVE && targetSteps<positionSteps))?-1:1;
  if(direction<0 && limitActive()){stopMotion("LIMIT_ACTIVE");return;}
  unsigned long nowUs=micros();
  float dt=min(0.02f,static_cast<float>(nowUs-lastRampUs)/1e6f);lastRampUs=nowUs;
  float wanted=maxSpeed;
  if(phase==MOVE || phase==HOME_BACKOFF){
    float remaining=static_cast<float>(labs(targetSteps-positionSteps))/STEPS_PER_MM;
    wanted=min(wanted,sqrtf(2.f*ACCEL_MM_S2*remaining));
  }
  speed=max(0.5f,min(wanted,speed+ACCEL_MM_S2*dt));
  unsigned long interval=static_cast<unsigned long>(1e6f/(speed*STEPS_PER_MM));
  if(nowUs-lastStepUs<interval)return;
  lastStepUs=nowUs;
  if(direction<0){digitalWrite(CCW_A,LOW);digitalWrite(CCW_B,LOW);downMotor.step(1);}
  else {digitalWrite(CW_A,LOW);digitalWrite(CW_B,LOW);upMotor.step(1);}
  if(phase==HOME_SEEK || phase==HOME_RELEASE)++homeTravel;
  else positionSteps+=direction;
}
void setup(){
  // Hold first, no automatic home, and never pulse on startup.
  digitalWrite(AWO,LOW);pinMode(AWO,OUTPUT);
  pinMode(LIMIT_PIN,INPUT_PULLUP);pulsesOff();
  downMotor.setSpeed(1000);upMotor.setSpeed(1000);
  Serial.begin(115200);
}
void loop(){
  readCommands();motionTick();
  if(modern && Serial && millis()-lastStatus>=STATUS_MS){lastStatus=millis();state();}
}
