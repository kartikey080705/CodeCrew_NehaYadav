// Arduino Code for Smart Agriculture Project - Responsive Edition
// This code uses non-blocking timing to ensure instant command response.

const int ledPin = LED_BUILTIN;
const int trigPin = 3; // HC-SR04 Trig
const int echoPin = 4; // HC-SR04 Echo
unsigned long lastSendTime = 0;
const long interval = 2000; // Send sensor data every 2 seconds

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  digitalWrite(ledPin, LOW);
}

void loop() {
  // 1. Process Commands INSTANTLY (No delay anymore!)
  while (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      digitalWrite(ledPin, HIGH);
    } else if (command == '0') {
      digitalWrite(ledPin, LOW);
    }
  }

  // 2. Broadcast Sensor Data on a Non-blocking Timer
  unsigned long currentTime = millis();
  if (currentTime - lastSendTime >= interval) {
    lastSendTime = currentTime;

    // Read Ultrasonic Distance (Placeholder/Calculated)
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    long duration = pulseIn(echoPin, HIGH);
    float distance = duration * 0.034 / 2;
    if (distance > 400 || distance < 2) distance = 0; // Out of range

    // Send to Python: soil, temp, hum, distance
    Serial.print(soil);
    Serial.print(",");
    Serial.print(temp);
    Serial.print(",");
    Serial.print(hum);
    Serial.print(",");
    Serial.println(distance);
  }
}
