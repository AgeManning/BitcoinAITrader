#!/usr/bin/python

import pymysql
import json


ImportFile = "Data.dat"

File = open(ImportFile, "r")

Object = json.loads(File.read())

