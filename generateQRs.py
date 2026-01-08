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
        fileName = name.replace(" ", "")
        studentDir = f"{outputDir}/{fileName}"
        if not os.path.exists(studentDir):
            os.makedirs(studentDir)
        img.save(f"{studentDir}/{fileName}.png")
        if not os.path.exists(f"{studentDir}/email.txt"):
            with open(f"{studentDir}/email.txt", "w") as emailFile:
                emailFile.write(email);

