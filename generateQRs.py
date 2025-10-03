#!/usr/bin/python3
import csv
import qrcode
import sys
import os

if len(sys.argv) != 3:
    print("Incorrect number of arguments. Expects format: generateQRs.py <csvPath> <output directory>")
    exit()

csvPath = sys.argv[1]
outputDir = sys.argv[2]
if not os.path.exists(outputDir):
    os.makedirs(outputDir)

with open(csvPath) as csvFile:
    reader = csv.reader(csvFile)
    for row in reader:
        email = row[1]
        name = row[2]
        print(f"Generating QR Code of {email} for {name}")
        img = qrcode.make(email)
        img.save(f"{outputDir}/{name}.png")