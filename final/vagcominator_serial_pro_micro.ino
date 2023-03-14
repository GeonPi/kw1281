/*
#ifndef TEST
#define TEST
#endif
*/
const int pinWriteK = 2;
const int pinReadK  = 3;
const unsigned int waitW = 785; //µs (tend to be really peaky)
const unsigned int waitR = 760; //µs (tend to be really peaky)
byte data = 0;
byte stop  = 192;             //0xC0 LSB
byte noData = 144;            //0x90 LSB
byte packetHeader[3];         //[0] = packet size; [1] = counter; [2] = id packet
byte cmd[3] = {144, 0, 0};    //[0] = command; [1] = id group; [2] = "\n"
byte cmdInit = 0;
byte cmdHome = 144;           //0x90 LSB
byte cmdError = 224;          //0xE0 LSB
byte cmdClear = 160;          //0xA0 LSB
byte cmdMeasuring = 148;      //0x94 LSB

bool initialized = false;
bool sendOk = false;

void setup() 
{
  Serial.begin(2000000);
  pinMode(pinWriteK, OUTPUT);
  pinMode(pinReadK,  INPUT);

  while(!Serial);
  Serial.println("Ready");
}

void loop() 
{
  if(initialized)
  {
    sendCommand();
    receivePacket();
  }
  else
  {
    readCmd();
    if(cmd[0] == cmdInit)
    {
      cmd[0] = cmdHome;
      initCom();
      initialized = true;
      receivePacket();
    }
  }
}

void initCom()
{
  #ifdef TEST
    Serial.println("Sending init sequence...");
  #endif

  sendPulse(HIGH, 205);
  sendPulse(LOW, 188);
  sendPulse(HIGH, 1429);
  sendPulse(LOW, 10);

  #ifdef TEST
    Serial.println("Finished!");
  #endif

  readByte();          //x55 (baud)
  readByte();          //x01 (counter)
  readByte();          //x8A
  sendComplement();
}

void readCmd()
{
  int i = 0;
  while(Serial.available())
  {
    cmd[i] = Serial.read();
    if(i == 0)
    {
      switch(cmd[0])
        {
          case 'I': cmd[0] = cmdInit; break;
          case 'H': cmd[0] = cmdHome; break;
          case 'E': cmd[0] = cmdError; break;
          case 'C': cmd[0] = cmdClear; break;
          case 'M': cmd[0] = cmdMeasuring; break;
          default:  cmd[0] = cmdHome; break;
        }
    }
    else if(cmd[1] != '\n' && i == 1) //id group
      cmd[1] = cmd[1] - 48;
    i++;
    sendOk = true;
  }

  if(sendOk)
  {
    Serial.println("OK");
    sendOk = false;
  }
}



void receivePacket()
{
  #ifdef TEST
    Serial.println("-------------------------------------------- receivePacket()");
  #endif

  #ifndef TEST
      Serial.println("start");
  #endif

  int i;
  for(i = 0; i < 3; i++)      //reading header
  {
    readByte();
    if(i == 0 | i == 1)
      packetHeader[i] = lsbToMsb(data); //revert "packet size" and "counter" to MSB
    else
      packetHeader[i] = data;
    #ifndef TEST
      sendDataOverSerial();
    #endif
    sendComplement();
  }
  
  #ifdef TEST
    Serial.print("Packet size: ");
    Serial.println(packetHeader[0]);
    Serial.print("Counter: ");
    Serial.println(packetHeader[1]);
  #endif

  if(packetHeader[0] == 3) //packet size == 3, no more data
  {
    readByte();
    #ifndef TEST
      sendDataOverSerial();
      Serial.println("stop");
    #endif
    cmd[0] = cmdHome;
    return;
  }
  #ifdef TEST
    Serial.println("********Data packet********");
  #endif
  for(i = 0; i < packetHeader[0] - 3; i++) //packet size
  {
    readByte();
    #ifndef TEST
      sendDataOverSerial();
    #endif
    sendComplement();
  }
  readByte(); //stop packet
  #ifndef TEST
      sendDataOverSerial();
      Serial.println("stop");
    #endif
  #ifdef TEST
    Serial.println("********Data packet end.********");
  #endif
}

void sendCommand()
{
  packetHeader[1]++;
  readCmd();

  #ifdef TEST
    Serial.println("-------------------------------------------- sendCommand()");
    Serial.print("Counter: ");
    Serial.println(packetHeader[1]);
  #endif

  if(cmd[0] == cmdMeasuring)
  {
    sendByte(4, true);                   //packet size
    readByte();
    sendByte(packetHeader[1], true);     //counter
    readByte();
    sendByte(cmd[0], false);             //command measuring group
    readByte();
    sendByte(cmd[1], true);              //id group
    readByte();
    sendByte(stop, false);               //stop
  }
  else //cmdHome | cmdError | cmdClear
  {
    sendByte(3, true);                   //packet size
    readByte();
    sendByte(packetHeader[1], true);     //counter
    readByte();
    sendByte(cmd[0], false);             //command
    readByte();
    sendByte(stop, false);               //stop
    cmd[0] = cmdHome;
  }
}

byte lsbToMsb(byte a)
{
  int i, j;
  byte b;
  for(i = 7, j = 0; i > -1; i--, j++)
    bitWrite(b, j, bitRead(a, i));
  return b;
}

void sendByte(byte a, bool revert)
{
  /*
  / if "a" is already LSB no need to set "revert" to true,
  / otherwise set "revert" to true for MSB
  */
  int i;
  delay(25);
  sendStartBit();
  if(revert)
  {
    for(i = 0; i < 8; i++)
    {
      int bit = bitRead(a, i) ? 0 : 1;
      digitalWrite(pinWriteK, bit);
      #ifdef TEST
        Serial.print(bit);
      #endif
      delayMicroseconds(waitW);
    }
    #ifdef TEST
      Serial.println("r");
    #endif
  }
  else
  {
    for(i = 7; i > -1; i--)
    {
      int bit = bitRead(a, i) ? 0 : 1;
      digitalWrite(pinWriteK, bit);
      #ifdef TEST
        Serial.print(bit);
      #endif
      delayMicroseconds(waitW);
    }
    #ifdef TEST
      Serial.println();
    #endif
  }
  sendStopBit();
}

void sendDataOverSerial()
{
  Serial.println(data, BIN);
}

void sendStartBit()
{
  digitalWrite(pinWriteK, HIGH);
  delayMicroseconds(waitW);
}

void sendStopBit()
{
  digitalWrite(pinWriteK, LOW);
  delayMicroseconds(waitW);
}

void sendComplement()
{
  delay(25);
  sendStartBit();
  for(int i = 7; i > -1; i--)
  {
    digitalWrite(pinWriteK, bitRead(data, i));
    delayMicroseconds(waitW);
  }
  #ifdef TEST
    Serial.println("send complement");
  #endif
  sendStopBit();
}

void readByte()
{
  while(1)
  {
    if(digitalRead(pinReadK) == LOW)
    {
      delayMicroseconds(waitR*2);
      for(int i = 0; i < 8; i++)
      {
        int bit = digitalRead(pinReadK);
        data = (data << 1) + bit;
        #ifdef TEST
          Serial.print(bit);
        #endif
        delayMicroseconds(waitR);
      }
      #ifdef TEST
        Serial.print("\t");
        Serial.println(data, HEX);
      #endif
      break;
    }
  }
}

void sendPulse(unsigned int state, unsigned long ms)
{
  digitalWrite(pinWriteK, state);
  delay(ms);
}
