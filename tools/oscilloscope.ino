
void setup() 
{
  Serial.begin(2000000);
}


void loop() 
{
  Serial.println(analogRead(A0));
}
