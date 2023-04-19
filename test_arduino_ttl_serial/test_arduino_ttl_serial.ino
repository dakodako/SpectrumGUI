String incomingByte;    
#define TTL_PIN 8
void setup() {

  Serial.begin(9600);

  pinMode(TTL_PIN, OUTPUT);

}
void loop() {

  if (Serial.available() > 0) {

  incomingByte = Serial.readStringUntil('\n');

    if (incomingByte == "on") {

      digitalWrite(TTL_PIN, HIGH);

      Serial.write("pin on");

    }

    else if (incomingByte == "off") {

      digitalWrite(TTL_PIN, LOW);

      Serial.write("pin off");

    }

    else{

     Serial.write("invalid input");

    }

  }

}