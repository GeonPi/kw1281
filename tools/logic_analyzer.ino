
const int pinReadK = 2;
const unsigned int wait = 770; //µs
volatile bool writing = false;

void setup() 
{
  Serial.begin(2000000);
  pinMode(pinReadK, INPUT_PULLUP);
}

void loop() 
{
  detectStartBit();
}

void detectStartBit()
{
  if(digitalRead(pinReadK) == LOW)
  {
    delayMicroseconds(wait*2);
    readByte();
  }
}

void readByte()
{
  int data = 0;
  for(int i = 0; i < 8; i++)
  {
    int bit = digitalRead(pinReadK);
    data = (data << 1) + bit;
    Serial.print(bit);
    delayMicroseconds(wait);
  }

  Serial.print("\t");
  Serial.println(data, HEX);
}
