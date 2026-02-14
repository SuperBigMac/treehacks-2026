// Water control: '0' off, '1' on, '2' pulse, '3' heartbeat.
// RX buffer is only 64 bytes (hardware limit). Pasting 60+ chars in Serial Monitor can
// overflow and reset the board — paste in chunks of ~50, or use the Python app (rate-limited).
// We drain by reading all bytes and applying only the LAST command to clear the buffer fast.

const int signalPin = 8;

// No serial byte for this long -> assume host disconnected -> shut off (as if "0")
const unsigned long DISCONNECT_TIMEOUT_MS = 500;
const unsigned long PULSE_MS = 100;

unsigned long lastReceivedMs = 0;   // 0 = never received
unsigned long pulseOffAt = 0;      // millis() when '2' pulse should end (0 = not pulsing)

void setup() {
  Serial.begin(9600);
  pinMode(signalPin, OUTPUT);
  digitalWrite(signalPin, LOW);
  delay(100);
  while (Serial.available() > 0) Serial.read();  // clear junk after reset
}

void loop() {
  unsigned long now = millis();

  // End '2' pulse when timer expires (non-blocking so we never delay() during serial read)
  if (pulseOffAt != 0 && now >= pulseOffAt) {
    digitalWrite(signalPin, LOW);
    pulseOffAt = 0;
  }

  // No serial for too long -> treat as disconnected -> shut off
  if (lastReceivedMs != 0 && (now - lastReceivedMs) > DISCONNECT_TIMEOUT_MS) {
    digitalWrite(signalPin, LOW);
    pulseOffAt = 0;
    lastReceivedMs = 0;
  }

  // Drain buffer as fast as possible: read all bytes, apply only the last command.
  // That way we do minimal work per byte and reduce chance of overflow on big paste.
  char lastCmd = 0;
  while (Serial.available() > 0) {
    lastReceivedMs = millis();
    lastCmd = Serial.read();
  }
  if (lastCmd == '1') {
    digitalWrite(signalPin, HIGH);
    pulseOffAt = 0;
  }
  else if (lastCmd == '0') {
    digitalWrite(signalPin, LOW);
    pulseOffAt = 0;
  }
  else if (lastCmd == '2') {
    digitalWrite(signalPin, HIGH);
    pulseOffAt = millis() + PULSE_MS;
  }
  // '3' and anything else: heartbeat / no-op (timer already updated above)
}
