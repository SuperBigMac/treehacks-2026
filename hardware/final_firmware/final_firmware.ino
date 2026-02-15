#include <Dynamixel2Arduino.h>

#define DXL_SERIAL   Serial1
#define DEBUG_SERIAL Serial
const int DXL_DIR_PIN = -1;   // OpenRB-150

Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);
using namespace ControlTableItem;

// Map letters -> Dynamixel IDs
const uint8_t SERVO_X_ID = 12;
const uint8_t SERVO_Y_ID = 11;

const int signalPin = 6;   // digital output pin

int angleToPositionX(int angle_deg)
{
  if (angle_deg < -90) {
    angle_deg = -90;
    DEBUG_SERIAL.println("clamped angle to -90 degrees");
  }
  if (angle_deg > 90) {
    angle_deg = 90;
    DEBUG_SERIAL.println("clamped angle to 90 degrees");
  }
  return (int)((-1 * angle_deg + 180) * 4095 / 360);
}

int angleToPositionY(int angle_deg)
{
  if (angle_deg < -20) {
    angle_deg = -20;
    DEBUG_SERIAL.println("clamped angle to -20 degrees");
  }
  if (angle_deg > 90) {
    angle_deg = 90;
    DEBUG_SERIAL.println("clamped angle to 90 degrees");
  }
  return (int)((angle_deg + 180) * 4095 / 360);
}

void initServo(uint8_t id)
{
  if (!dxl.ping(id)) {
    DEBUG_SERIAL.print("NOT FOUND ID ");
    DEBUG_SERIAL.println(id);
    return;
  }

  dxl.torqueOff(id);
  dxl.setOperatingMode(id, OP_POSITION);
  dxl.torqueOn(id);

  DEBUG_SERIAL.print("Ready ID ");
  DEBUG_SERIAL.println(id);
}

void setup()
{
  DEBUG_SERIAL.begin(115200);
  while (!DEBUG_SERIAL);

  pinMode(signalPin, OUTPUT);

  DEBUG_SERIAL.println("=============== SETUP ============== ");

  dxl.begin(1000000);
  dxl.setPortProtocolVersion(2.0);

  initServo(SERVO_X_ID);
  initServo(SERVO_Y_ID);

  DEBUG_SERIAL.println("=================================== ");
  DEBUG_SERIAL.println("Servo: x <deg: [-90, 90]> or y <deg: [-20, 90]>");
  DEBUG_SERIAL.println("Digital: 0=LOW, 1=HIGH, 2=PULSE");
  DEBUG_SERIAL.println("=================================== ");
}

void loop()
{
  if (!DEBUG_SERIAL.available()) return;

  String line = DEBUG_SERIAL.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  // check digital commands
  if (line == "0") {
    digitalWrite(signalPin, LOW);
    DEBUG_SERIAL.println("Signal pin LOW");
    return;
  }
  if (line == "1") {
    digitalWrite(signalPin, HIGH);
    DEBUG_SERIAL.println("Signal pin HIGH");
    return;
  }
  if (line == "2") {
    DEBUG_SERIAL.println("Signal pin PULSE");
    digitalWrite(signalPin, LOW);
    digitalWrite(signalPin, HIGH);
    delay(100);
    digitalWrite(signalPin, LOW);
    return;
  }

  // otherwise assume servo command: "<letter> <number>"
  char which = line.charAt(0);

  int sep = line.indexOf(' ');
  if (sep < 0) sep = line.indexOf('\t');
  if (sep < 0) {
    DEBUG_SERIAL.print("Bad input: ");
    DEBUG_SERIAL.println(line);
    return;
  }

  String num = line.substring(sep + 1);
  num.trim();
  if (num.length() == 0) {
    DEBUG_SERIAL.print("Bad input: ");
    DEBUG_SERIAL.println(line);
    return;
  }

  int ang = num.toInt();
  uint8_t id;
  int pos = 0;

  if (which == 'x' || which == 'X') {
    id = SERVO_X_ID;
    pos = angleToPositionX(ang);
  } else if (which == 'y' || which == 'Y') {
    id = SERVO_Y_ID;
    pos = angleToPositionY(ang);
  } else {
    DEBUG_SERIAL.print("Unknown servo (use x or y): ");
    DEBUG_SERIAL.println(which);
    return;
  }

  DEBUG_SERIAL.print("Servo ");
  DEBUG_SERIAL.print((char)tolower(which));
  DEBUG_SERIAL.print(" (ID ");
  DEBUG_SERIAL.print(id);
  DEBUG_SERIAL.print(") -> angle ");
  DEBUG_SERIAL.print(ang);
  DEBUG_SERIAL.print(" deg (pos ");
  DEBUG_SERIAL.print(pos);
  DEBUG_SERIAL.println(")");

  dxl.setGoalPosition(id, pos);
}
