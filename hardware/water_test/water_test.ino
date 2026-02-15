// '0' off, '1' on, '2' pulse, '3' heartbeat (resets disconnect timer only)
const int signalPin = 8;

// No serial for this long -> assume host disconnected -> shut off (as if "0")
const unsigned long DISCONNECT_TIMEOUT_MS = 800;

unsigned long lastReceivedMs = 0;  // 0 = never received

void setup() {
  Serial.begin(9600);
  pinMode(signalPin, OUTPUT);
  digitalWrite(signalPin, LOW);
}

void loop() {
  // If we've received at least one byte and it's been too long, treat as disconnected
  if (lastReceivedMs != 0 && (millis() - lastReceivedMs) > DISCONNECT_TIMEOUT_MS) {
    digitalWrite(signalPin, LOW);
    lastReceivedMs = 0;
  }

  if (Serial.available() > 0) {
    char input = Serial.read();
    lastReceivedMs = millis();

    if (input == '1') {
      digitalWrite(signalPin, HIGH);
    }
    else if (input == '0') {
      digitalWrite(signalPin, LOW);
    }
    else if (input == '2') {
      digitalWrite(signalPin, LOW);
      digitalWrite(signalPin, HIGH);
      delay(100);
      digitalWrite(signalPin, LOW);
    }
    // '3' = heartbeat only (timer already updated above; no pin change)
  }
}