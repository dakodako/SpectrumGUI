String incomingByte;    
#define LED_PIN 8
void setup() {

  Serial.begin(9600);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

}
void loop() {

  if (Serial.available() > 0) {

  incomingByte = Serial.readStringUntil('\n');

    if (incomingByte == "on") {

      digitalWrite(LED_PIN, HIGH);

      Serial.write("Led on");

    }

    else if (incomingByte == "off") {

      digitalWrite(LED_PIN, LOW);

      Serial.write("Led off");

    }

    else{

     Serial.write("invalid input");

    }

  }

}