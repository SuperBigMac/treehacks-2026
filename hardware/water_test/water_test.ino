const int signalPin = 8;

void setup() {
  Serial.begin(9600);
  pinMode(signalPin, OUTPUT);
}

void loop() {

  // Check if data is available from serial
  if (Serial.available() > 0) {

    char input = Serial.read();

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
  }
}