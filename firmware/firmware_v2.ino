const int pinWrite = 2;
const int pinRead = 3;
const unsigned int waitW = 785; //µs
const unsigned int waitR = 770; //µs
byte data = 0;

void setup()
{
  Serial.begin(2000000);
  pinMode(pinWrite, OUTPUT);

  while(!Serial);   //uncomment if you use an Arduino Pro Micro
  initCom();
}

void loop()
{
  readByte();
  sendComplement();
}

void initCom()
{
	Serial.println("Sending init sequence...");

	sendPulse(HIGH, 205);
	sendPulse(LOW, 188);
	sendPulse(HIGH, 1429);
	sendPulse(LOW, 10);
 
	Serial.println("Finished!");

  readByte();          //x55
  readByte();          //x01
  readByte();          //x8A
  sendComplement();
}

void sendPulse(unsigned int state, unsigned long ms)
{
	digitalWrite(pinWrite, state);
	delay(ms);
}

void readByte()
{
  while(1)
  {
    if(digitalRead(pinRead) == LOW)
    {
      delayMicroseconds(waitR * 2);
      for(int i = 0; i < 8; i++)
      {
        int bit = digitalRead(pinRead);
        data = (data << 1) + bit;
        Serial.print(bit);
        delayMicroseconds(waitR);
      }
        Serial.print("\t");
        Serial.println(data, HEX);
      break;
    }
  }
}

void sendComplement()
{
  delay(25);
  sendStartBit();
  for(int i = 7; i > -1; i--)
  {
    digitalWrite(pinWrite, bitRead(data, i));
    delayMicroseconds(waitW);
  }
  Serial.println("send complement");
  sendStopBit();
}

void sendStartBit()
{
  digitalWrite(pinWrite, HIGH);
  delayMicroseconds(waitW);
}

void sendStopBit()
{
  digitalWrite(pinWrite, LOW);
  delayMicroseconds(waitW);
}
