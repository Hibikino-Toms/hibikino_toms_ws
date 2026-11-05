#include <Arduino.h>
#include <SPI.h>
#include <mcp2515.h>
#include <stdlib.h>
#include <string.h>

// RMD-X6 ID 1 and RMD-X8 ID 0, via Uno R3 + MCP2515 (8 MHz crystal).
// The bridge never starts motion on boot. It sends position goals only after
// CONFIG and ARM have both been accepted from the ROS host.
namespace {
constexpr uint8_t kCanCsPin = 10;
#ifndef BRIDGE_SPI_HZ
#define BRIDGE_SPI_HZ 1000000UL
#endif
constexpr uint8_t kX8Id = 0;
constexpr uint8_t kX6Id = 1;
constexpr uint16_t kMinVoltage10 = 200;  // 20.0 V
constexpr uint16_t kMaxVoltage10 = 550;  // 55.0 V
constexpr int16_t kStoppedDps = 10;
constexpr uint16_t kMaxSpeedDps = 60;
constexpr unsigned long kCanReplyTimeoutMs = 100;
constexpr unsigned long kHostTimeoutMs = 500;
constexpr uint8_t kCanInitAttempts = 10;
constexpr unsigned long kCanInitRetryMs = 150;
constexpr size_t kLineBufferSize = 112;

// Pass SPI explicitly so its peripheral setup happens inside setup(), after
// Arduino core initialization, instead of a global object's constructor.
MCP2515 canController(kCanCsPin, BRIDGE_SPI_HZ, &SPI);
struct can_frame txFrame;
struct can_frame rxFrame;

struct MotorState {
  int32_t positionCdeg;
  int16_t speedDps;
  int8_t temperatureC;
  uint16_t voltage10;
  uint16_t errors;
};

MotorState x8 = {};
MotorState x6 = {};
int32_t x8MinCdeg = 0;
int32_t x8MaxCdeg = 0;
int32_t x6MinCdeg = 0;
int32_t x6MaxCdeg = 0;
bool canReady = false;
bool configured = false;
bool armed = false;
unsigned long lastHostMs = 0;
char lineBuffer[kLineBufferSize];
size_t lineLength = 0;
bool discardLine = false;

uint8_t diagnosticRegister(uint8_t address, uint32_t clockHz = BRIDGE_SPI_HZ) {
  SPI.beginTransaction(SPISettings(clockHz, MSBFIRST, SPI_MODE0));
  digitalWrite(kCanCsPin, LOW);
  SPI.transfer(0x03);
  SPI.transfer(address);
  uint8_t value = SPI.transfer(0);
  digitalWrite(kCanCsPin, HIGH);
  SPI.endTransaction();
  return value;
}

void printCanRegisters(uint32_t clockHz = BRIDGE_SPI_HZ) {
  const uint8_t addresses[] = {0x0e, 0x0f, 0x28, 0x29, 0x2a, 0x2c, 0x2d, 0x1c, 0x1d, 0x30, 0x40, 0x50};
  Serial.print(F(",spi_hz=")); Serial.print(clockHz);
  for (uint8_t address : addresses) {
    Serial.print(F(",reg")); Serial.print(address, HEX);
    Serial.print('='); Serial.print(diagnosticRegister(address, clockHz), HEX);
  }
  Serial.println();
}

int16_t readInt16LE(uint8_t low, uint8_t high) {
  return static_cast<int16_t>((static_cast<uint16_t>(high) << 8) | low);
}

uint16_t readUint16LE(uint8_t low, uint8_t high) {
  return static_cast<uint16_t>(low) | (static_cast<uint16_t>(high) << 8);
}

int32_t readInt32LE(const uint8_t *data) {
  const uint32_t value = static_cast<uint32_t>(data[0]) |
      (static_cast<uint32_t>(data[1]) << 8) |
      (static_cast<uint32_t>(data[2]) << 16) |
      (static_cast<uint32_t>(data[3]) << 24);
  return static_cast<int32_t>(value);
}

void writeInt32LE(uint8_t *data, int32_t value) {
  const uint32_t word = static_cast<uint32_t>(value);
  data[0] = static_cast<uint8_t>(word);
  data[1] = static_cast<uint8_t>(word >> 8);
  data[2] = static_cast<uint8_t>(word >> 16);
  data[3] = static_cast<uint8_t>(word >> 24);
}

MotorState &stateFor(uint8_t motorId) {
  return motorId == kX8Id ? x8 : x6;
}

const char *nameFor(uint8_t motorId) {
  return motorId == kX8Id ? "X8_ID0" : "X6_ID1";
}

bool sendFrame(uint8_t motorId, uint8_t command, uint16_t speedDps = 0,
               int32_t positionCdeg = 0) {
  txFrame.can_id = 0x140 + motorId;
  txFrame.can_dlc = 8;
  memset(txFrame.data, 0, sizeof(txFrame.data));
  txFrame.data[0] = command;
  if (command == 0xA4) {
    txFrame.data[2] = static_cast<uint8_t>(speedDps);
    txFrame.data[3] = static_cast<uint8_t>(speedDps >> 8);
    writeInt32LE(&txFrame.data[4], positionCdeg);
  }
  return canController.sendMessage(&txFrame) == MCP2515::ERROR_OK;
}

bool query(uint8_t motorId, uint8_t command, struct can_frame &reply) {
  if (!sendFrame(motorId, command)) {
    Serial.print(F("DIAG,CAN_TX,id=")); Serial.print(motorId);
    Serial.print(F(",cmd=")); Serial.print(command, HEX);
    printCanRegisters();
    return false;
  }
  const uint16_t expectedId = 0x240 + motorId;
  const unsigned long started = millis();
  uint8_t received = 0;
  uint32_t lastId = 0;
  uint8_t lastCommand = 0;
  while (millis() - started < kCanReplyTimeoutMs) {
    while (canController.readMessage(&rxFrame) == MCP2515::ERROR_OK) {
      ++received; lastId=rxFrame.can_id; lastCommand=rxFrame.data[0];
      if (rxFrame.can_id == expectedId && rxFrame.can_dlc == 8 &&
          rxFrame.data[0] == command) {
        memcpy(&reply, &rxFrame, sizeof(reply));
        if (millis()-started >= 20) {
          Serial.print(F("DIAG,CAN_LATE,id=")); Serial.print(motorId);
          Serial.print(F(",cmd=")); Serial.print(command, HEX);
          Serial.print(F(",elapsed_ms=")); Serial.println(millis()-started);
        }
        return true;
      }
    }
    delay(1);
  }
  Serial.print(F("DIAG,CAN_QUERY_TIMEOUT,id=")); Serial.print(motorId);
  Serial.print(F(",cmd=")); Serial.print(command, HEX);
  Serial.print(F(",elapsed_ms=")); Serial.print(millis()-started);
  Serial.print(F(",rx_count=")); Serial.print(received);
  Serial.print(F(",last_id=")); Serial.print(lastId, HEX);
  Serial.print(F(",last_cmd=")); Serial.print(lastCommand, HEX);
  printCanRegisters();
  return false;
}

bool readMotor(uint8_t motorId) {
  struct can_frame status1;
  struct can_frame status2;
  struct can_frame angle;
  if (!query(motorId, 0x9A, status1) ||
      !query(motorId, 0x9C, status2) ||
      !query(motorId, 0x92, angle)) {
    return false;
  }
  MotorState &state = stateFor(motorId);
  state.temperatureC = static_cast<int8_t>(status2.data[1]);
  state.speedDps = readInt16LE(status2.data[4], status2.data[5]);
  state.voltage10 = readUint16LE(status1.data[4], status1.data[5]);
  state.errors = readUint16LE(status1.data[6], status1.data[7]);
  state.positionCdeg = readInt32LE(&angle.data[4]);
  return true;
}

void stopBoth() {
  sendFrame(kX8Id, 0x81);
  sendFrame(kX6Id, 0x81);
}

bool preflight() {
  if (!readMotor(kX8Id) || !readMotor(kX6Id)) return false;
  const MotorState *states[2] = {&x8, &x6};
  const int32_t lows[2] = {x8MinCdeg, x6MinCdeg};
  const int32_t highs[2] = {x8MaxCdeg, x6MaxCdeg};
  const uint8_t ids[2] = {kX8Id, kX6Id};
  for (uint8_t i = 0; i < 2; ++i) {
    const MotorState &state = *states[i];
    if (state.errors != 0 || state.voltage10 < kMinVoltage10 ||
        state.voltage10 > kMaxVoltage10 ||
        state.speedDps < -kStoppedDps || state.speedDps > kStoppedDps ||
        state.positionCdeg < lows[i] || state.positionCdeg > highs[i]) {
      Serial.print(F("ERR,0,PREFLIGHT,")); Serial.print(nameFor(ids[i]));
      Serial.print(F(",error=0x")); Serial.print(state.errors, HEX);
      Serial.print(F(",voltage10=")); Serial.print(state.voltage10);
      Serial.print(F(",speedDps=")); Serial.print(state.speedDps);
      Serial.print(F(",positionCdeg=")); Serial.println(state.positionCdeg);
      return false;
    }
  }
  return true;
}

void printState(unsigned long sequence) {
  Serial.print(F("S,")); Serial.print(sequence);
  Serial.print(','); Serial.print(armed ? 1 : 0);
  Serial.print(','); Serial.print(x8.positionCdeg);
  Serial.print(','); Serial.print(x8.speedDps);
  Serial.print(','); Serial.print(x8.temperatureC);
  Serial.print(','); Serial.print(x8.voltage10);
  Serial.print(','); Serial.print(x8.errors);
  Serial.print(','); Serial.print(x6.positionCdeg);
  Serial.print(','); Serial.print(x6.speedDps);
  Serial.print(','); Serial.print(x6.temperatureC);
  Serial.print(','); Serial.print(x6.voltage10);
  Serial.print(','); Serial.println(x6.errors);
}

bool parseSequence(const char *line, const char *prefix, unsigned long &sequence) {
  char extra;
  char format[20];
  snprintf(format, sizeof(format), "%s,%%lu%%c", prefix);
  return sscanf(line, format, &sequence, &extra) == 1;
}

void handleLine(const char *line) {
  unsigned long sequence = 0;
  char extra;
  if (strcmp(line, "SPI_PINS") == 0 && !armed) {
    Serial.print(F("DIAG,PINS,pinb=")); Serial.println(PINB, HEX);
    pinMode(MISO, INPUT_PULLUP);
    delay(2);
    Serial.print(F("DIAG,PULLUP,pinb=")); Serial.print(PINB, HEX);
    printCanRegisters(500000UL);
    pinMode(MISO, INPUT);
    Serial.println(F("OK,SPI_PINS"));
    return;
  }
  if (strcmp(line, "SPI_CHECK") == 0 && !armed && canReady) {
    const uint32_t rates[] = {10000000UL, 4000000UL, 2000000UL, 1000000UL, 500000UL};
    const uint8_t regs[] = {0x28, 0x29, 0x2a, 0x0f};
    uint8_t expected[4];
    for (uint8_t j=0; j<4; ++j) expected[j] = diagnosticRegister(regs[j], 500000UL);
    for (uint32_t rate : rates) {
      uint16_t mismatches=0;
      for (uint16_t i=0; i<1000; ++i) {
        for (uint8_t j=0; j<4; ++j) {
          if (diagnosticRegister(regs[j], rate) != expected[j]) ++mismatches;
        }
      }
      Serial.print(F("DIAG,SPI_CHECK,hz=")); Serial.print(rate);
      Serial.print(F(",reads=4000,mismatches=")); Serial.println(mismatches);
    }
    Serial.println(F("OK,SPI_CHECK"));
    return;
  }
  if (strcmp(line, "PING") == 0) {
    lastHostMs = millis();
    Serial.println(F("PONG,RMD_ARM_V1"));
    return;
  }
  if (strcmp(line, "STOP") == 0) {
    stopBoth();
    armed = false;
    lastHostMs = millis();
    Serial.println(F("OK,STOP"));
    return;
  }
  if (sscanf(line, "CONFIG,%ld,%ld,%ld,%ld%c", &x8MinCdeg, &x8MaxCdeg,
             &x6MinCdeg, &x6MaxCdeg, &extra) == 4) {
    if (armed || x8MinCdeg >= x8MaxCdeg || x6MinCdeg >= x6MaxCdeg ||
        x8MinCdeg < -72000L || x8MaxCdeg > 72000L ||
        x6MinCdeg < -72000L || x6MaxCdeg > 72000L) {
      configured = false;
      Serial.println(F("ERR,0,CONFIG_REJECTED"));
      return;
    }
    configured = true;
    lastHostMs = millis();
    Serial.println(F("OK,CONFIG"));
    return;
  }
  if (strcmp(line, "ARM") == 0) {
    if (!canReady || !configured) {
      armed = false;
      Serial.println(F("ERR,0,NOT_CONFIGURED"));
      return;
    }
    stopBoth();
    delay(3);
    if (!preflight()) {
      armed = false;
      return;
    }
    armed = true;
    lastHostMs = millis();
    Serial.println(F("OK,ARMED"));
    return;
  }
  if (strcmp(line, "HB") == 0) {
    if (armed) {
      lastHostMs = millis();
      Serial.println(F("OK,HB"));
    } else {
      Serial.println(F("ERR,0,NOT_ARMED"));
    }
    return;
  }
  if (sscanf(line, "READ,%lu%c", &sequence, &extra) == 1) {
    if (!canReady) {
      Serial.print(F("ERR,")); Serial.print(sequence);
      Serial.println(F(",MCP2515_NOT_READY"));
      return;
    }
    lastHostMs = millis();
    if (!readMotor(kX8Id) || !readMotor(kX6Id)) {
      Serial.print(F("ERR,")); Serial.print(sequence);
      Serial.println(F(",CAN_TIMEOUT"));
      if (armed) stopBoth();
      armed = false;
      return;
    }
    printState(sequence);
    if (armed && (x8.errors != 0 || x6.errors != 0 ||
        x8.voltage10 < kMinVoltage10 || x8.voltage10 > kMaxVoltage10 ||
        x6.voltage10 < kMinVoltage10 || x6.voltage10 > kMaxVoltage10)) {
      stopBoth();
      armed = false;
      Serial.println(F("FAULT,CAN_MOTOR_STATUS"));
    }
    return;
  }
  int32_t x8Target = 0;
  int32_t x6Target = 0;
  unsigned int x8Speed = 0;
  unsigned int x6Speed = 0;
  if (sscanf(line, "MOVE,%lu,%ld,%ld,%u,%u%c", &sequence, &x8Target,
             &x6Target, &x8Speed, &x6Speed, &extra) == 5) {
    lastHostMs = millis();
    if (!armed || !configured) {
      Serial.print(F("ERR,")); Serial.print(sequence);
      Serial.println(F(",NOT_ARMED"));
      return;
    }
    if (x8Target < x8MinCdeg || x8Target > x8MaxCdeg ||
        x6Target < x6MinCdeg || x6Target > x6MaxCdeg ||
        x8Speed == 0 || x8Speed > kMaxSpeedDps ||
        x6Speed == 0 || x6Speed > kMaxSpeedDps) {
      stopBoth();
      armed = false;
      Serial.print(F("ERR,")); Serial.print(sequence);
      Serial.println(F(",COMMAND_LIMIT"));
      return;
    }
    if (!sendFrame(kX8Id, 0xA4, x8Speed, x8Target) ||
        !sendFrame(kX6Id, 0xA4, x6Speed, x6Target)) {
      stopBoth();
      armed = false;
      Serial.print(F("ERR,")); Serial.print(sequence);
      Serial.println(F(",CAN_TX"));
      return;
    }
    Serial.print(F("OK,MOVE,")); Serial.println(sequence);
    return;
  }
  if (parseSequence(line, "READ", sequence)) {
    Serial.println(F("ERR,0,BAD_READ"));
    return;
  }
  // Malformed commands fail closed if a position-control session was active.
  if (armed) {
    stopBoth();
    armed = false;
  }
  Serial.println(F("ERR,0,BAD_COMMAND"));
}

void serviceSerial() {
  for (uint8_t count = 0; count < 64 && Serial.available(); ++count) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\r') continue;
    if (value == '\n') {
      if (!discardLine && lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        handleLine(lineBuffer);
      }
      lineLength = 0;
      discardLine = false;
    } else if (!discardLine && lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = value;
    } else {
      discardLine = true;
    }
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  // Initialize the SPI peripheral after Arduino core initialization.
  SPI.begin();
  pinMode(kCanCsPin, OUTPUT);
  digitalWrite(kCanCsPin, HIGH);
  delay(50);
  uint8_t stage = 1;
  uint8_t attemptsUsed = 0;
  MCP2515::ERROR result = MCP2515::ERROR_FAIL;
  for (uint8_t attempt = 1; attempt <= kCanInitAttempts; ++attempt) {
    attemptsUsed = attempt;
    digitalWrite(kCanCsPin, HIGH);
    delay(2);
    stage = 1; result = canController.reset();
    if (result == MCP2515::ERROR_OK) {
      stage = 2; result = canController.setBitrate(CAN_1000KBPS, MCP_8MHZ);
    }
    if (result == MCP2515::ERROR_OK) {
      stage = 3; result = canController.setNormalMode();
    }
    if (result == MCP2515::ERROR_OK &&
        (diagnosticRegister(0x2a) != MCP_8MHz_1000kBPS_CFG1 ||
         diagnosticRegister(0x29) != MCP_8MHz_1000kBPS_CFG2 ||
         diagnosticRegister(0x28) != MCP_8MHz_1000kBPS_CFG3 ||
         (diagnosticRegister(0x0e) & 0xe0) != 0 ||
         (diagnosticRegister(0x0f) & 0xe0) != 0)) {
      stage = 4; result = MCP2515::ERROR_FAIL;
    }
    if (result == MCP2515::ERROR_OK) break;
    if (attempt < kCanInitAttempts) {
      Serial.print(F("DIAG,INIT_RETRY,attempt=")); Serial.print(attempt);
      Serial.print(F(",stage=")); Serial.print(stage);
      Serial.print(F(",result=")); Serial.print(result);
      printCanRegisters();
      delay(kCanInitRetryMs);
    }
  }
  if (result != MCP2515::ERROR_OK) {
    Serial.print(F("DIAG,AVR_SPI,spcr=")); Serial.print(SPCR, HEX);
    Serial.print(F(",ddrb=")); Serial.print(DDRB, HEX);
    Serial.print(F(",portb=")); Serial.println(PORTB, HEX);
    Serial.print(F("DIAG,INIT_SLOW_READ")); printCanRegisters(500000UL);
    Serial.print(F("ERR,0,MCP2515_INIT,stage=")); Serial.print(stage);
    Serial.print(F(",result=")); Serial.print(result);
    printCanRegisters();
    return;
  }
  Serial.print(F("DIAG,INIT_OK,attempt=")); Serial.print(attemptsUsed);
  printCanRegisters();
  canReady = true;
  stopBoth();
  delay(5);
  Serial.println(F("READY,RMD_ARM_V1,STOPPED"));
}

void loop() {
  serviceSerial();
  if (armed && millis() - lastHostMs > kHostTimeoutMs) {
    stopBoth();
    armed = false;
    Serial.println(F("FAULT,HOST_TIMEOUT"));
  }
}
