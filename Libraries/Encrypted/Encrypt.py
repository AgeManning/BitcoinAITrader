#!/usr/bin/python
import sys
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random

sys.argv[1] = sys.argv[1].split(',')
sys.argv[2] = sys.argv[2].split(',')

if len(sys.argv) != 4 or len(sys.argv[1]) != len(sys.argv[2]):
    print("Usage: python Encrypt file1,file2,file3 EncryptFile1,EncryptFile2,EncryptFile3 EncryptionKey")
    print("Ensure there is no spaces in the file lists.")
    sys.exit(1)


secret = sys.argv[3]
shash = SHA256.new(secret)
key = shash.digest()

FileNo = 0
for File in sys.argv[1]:
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, iv)

    EncryptFile = File
    OutFileName = sys.argv[2][FileNo]

    f = open(EncryptFile, "r")
    Encrypted = iv +  cipher.encrypt(f.read().encode('utf-8'))
    f.close()
    OutFile = open(OutFileName, "wb")
    OutFile.write(Encrypted)
    OutFile.close()
    FileNo +=1
