#!/bin/sh

cd Encrypted

python Encrypt.py ../BitCoinInterface.py,../TraderMain.py,../AI.py,../TraderDac.py EBitCoinInterface.age,ETraderMain.age,EAI.age,ETraderDac.age "BitCoinFunzies123"

cp *.age ../../Encrypted/Libraries/
