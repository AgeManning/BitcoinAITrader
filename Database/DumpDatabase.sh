#/bin/sh

mysqldump -u age -pHarri5on BitCoins > CurrentSnapshot.sql
mysqldump -u age -pHarri5on --routines --no-create-info --no-data --no-create-db --skip-opt BitCoins > Procedures.sql
