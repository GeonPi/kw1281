const int pinWrite = 2;

void setup()
{
    Serial.begin(2000000);
    pinMode(pinWrite, OUTPUT);

    //while(!Serial);   //uncomment if you use an Arduino Pro Micro
    initCom();
}

void loop()
{
}

void initCom()
{
    Serial.println("Sending init sequence...");

    sendPulse(HIGH, 205);
    sendPulse(LOW, 188);
    sendPulse(HIGH, 1429);
    sendPulse(LOW, 10);

    Serial.println("Finished!");
}

void sendPulse(unsigned int state, unsigned long ms)
{
    digitalWrite(pinWrite, state);
    delay(ms);
}
