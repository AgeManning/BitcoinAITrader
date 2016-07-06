from Crypto.Cipher import AES

def DecryptModules(Hash, modules):


    for Module in modules:
        DecryptFile = Module + ".age"
        OutputFile = Module[1:] + ".py"
        f = open(DecryptFile, "rb")
        Data = f.read()
        f.close()
        iv = Data[:AES.block_size]
        cipher = AES.new(Hash, AES.MODE_CFB, iv)
        Decrypt = cipher.decrypt(Data[AES.block_size:])

        OutFile = open(OutputFile, "w")
        OutFile.write(Decrypt.decode())
        OutFile.close()
