/*
著者：佐藤光
コード内容：一軸アクチュエータ(トマトロボットの高さ方向制御部)の制御
シリアルモニタの入力例:100mm移動する場合→100,0\n，-100mm移動する場合→-100,0\n
入力の種類
1. 0,0\n：モータへの電力供給OFF
2. 1,0\n：モータへの電力供給ON
3. 2,0\n：初期位置へ移動
4. 3,x\n：xmmの位置へ移動(x=0-450)
*/

//ステッピングモータを制御するためのライブラリ
#include <Stepper.h>

//ステッピングモータ用ピン設定
//cw時計回り(下方向)，ccw反時計回り(上方向)に回すピン
const int cwA  = 16;
const int cwB  = 17;
const int ccwA = 18;
const int ccwB = 19;
//モータに電力供給のON/OFFを指令するピン
const int awo  = 20;

//リミットスイッチ用ピン設定（実測：未押下=HIGH、押下/断線=LOW）
const int limit_switch = 26;
const int limit_active_level = LOW;

//Stepperライブラリ用の設定値
const int rotation_steps = 500; //1回転(360度)のステップ数(1ステップは0.72度)
const int rotation_speed = 1000; //RPMの設定(スピードの設定)
// オブジェクト生成
Stepper stepper_cw(rotation_steps, cwA,cwB);
Stepper stepper_ccw(rotation_steps, ccwA,ccwB);

volatile int mode = 0;
volatile int z_val = 0;

volatile int pre_pos = -1;  //現在の位置

//チャタリング防止処理用変数
int bounce=250;
int ct,pt;

void setup() {
  //シリアル通信初期化
  Serial.begin(115200);
  //ピンモードの設定
  pinMode(limit_switch, INPUT_PULLUP);
  pinMode(awo, OUTPUT);
  //RPM設定
  stepper_cw.setSpeed(rotation_speed);
  stepper_ccw.setSpeed(rotation_speed);

  //モータへの電力供給OFF
  power_enable(0);
}

//電力供給関数
void power_enable(bool state){
  if (state == true){
    digitalWrite(awo, LOW);//電力供給ON
    String str = String(1) + " " + String(0) + " ";
    Serial.println(str);
  }
  else{
    digitalWrite(awo,HIGH);//電力供給OFF
    String str = String(0) + " " + String(0) + " ";
    Serial.println(str);
  }
}

//ステッピングモータ停止関数
void cw_stop(){
  digitalWrite(cwA, LOW);
  digitalWrite(cwB, LOW);
}
void ccw_stop(){
  digitalWrite(ccwA, LOW);
  digitalWrite(ccwB, LOW);
}

//ステッピングモータ動作関数
void move_stepper(int goal_pos){
  //Serial.println(pre_pos);
  if(pre_pos>=0&&pre_pos<=450&&goal_pos>=0&&goal_pos<=450){
    int move_val = 0;
    move_val = goal_pos - pre_pos;//目標座標-現在の座標
    int move_step = 0; //動作させるステップ量
    move_step = 200*abs(move_val);//200ステップで1mm移動
    if(move_val >= 0){
      cw_stop();
      stepper_ccw.step(move_step);
      ccw_stop();
    }
    else{
      ccw_stop();
      stepper_cw.step(move_step);
      cw_stop();
    }
    print_pos(goal_pos);
  }
}

//初期位置移動関数
void init_pos(){
  // HIGH（未押下）の間だけ原点方向へ動かし、LOW（押下/断線）で停止する。
  while (digitalRead(limit_switch) != limit_active_level) {
    stepper_cw.step(200);  // 初期位置に向けてステッピングモータを動かす200
  }
  cw_stop();
  delay(50);

  //5mm上げる
  stepper_ccw.step(5000); // 5000
  ccw_stop();
  pre_pos = 5;

  // メインPCにシリアルで応答を返す
  String str = String(2) + " " + String(pre_pos) + " ";
  Serial.println(str);
}


void print_pos(int pos){
//  Serial.print("現在の位置:");
//  Serial.print(pos);
//  Serial.println("mm");
  pre_pos = pos;
  String str = String(3) + " " + String(pre_pos) + " ";
  Serial.println(str);
}

//送られてきたデータを配列に変換
int split(String data, char delimiter, String *dst){
  int index = 0;
  int arraySize = (sizeof(data))/sizeof((data[0]));
  int datalength = data.length();

  for(int i = 0; i < datalength; i++){
    char tmp = data.charAt(i);
    if( tmp == delimiter ){
      index++;
      if( index > (arraySize - 1)) return -1;
    }
    else dst[index] += tmp;
  }
  return (index + 1);
}

void loop() {
  //Serial.println("Z軸を何mm動かしますか？");
  String cmds[2];
  if(Serial.available() > 0){
    digitalWrite(awo, LOW);
    String input_cmd = Serial.readStringUntil('\n');
    int index = split(input_cmd, ',', cmds);
    mode = cmds[0].toInt();
    z_val = cmds[1].toInt();
    if(mode==0){power_enable(0);}
    else if(mode==1){power_enable(1);
    }
    else if(mode==2){init_pos();
    }
    else if(mode==3){
      if(z_val>=0){
        move_stepper(z_val);
      }
      else{
        String str = String(4) + " " + String(pre_pos) + " ";
      }
    }
    else{
      String str = String(5) + " " + String(pre_pos) + " ";
      Serial.println(str);
    }
  }
}
