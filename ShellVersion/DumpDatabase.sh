#/bin/sh

mysqldump -u age -p<password-Here> BitCoins > CurrentSnapshot.sql
mysqldump -u age -p<passwordHere> --routines --no-create-info --no-data --no-create-db --skip-opt BitCoins > Procedures.sql
