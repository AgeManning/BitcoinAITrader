#!/bin/sh

ssh Insomnia ./BitCoins/Database/DumpForRemote.sh

scp Insomnia:./BitCoins/Database/ShellDump.sql ~/Scripts/BitCoins/Database/Remote/

mysql -u age -p<password> BitCoins < ~/Scripts/BitCoins/Database/Remote/ShellDump.sql

mysql -u age -p<password> BitCoins < ~/Scripts/BitCoins/Database/Remote/UpdateTimeZone.sql
