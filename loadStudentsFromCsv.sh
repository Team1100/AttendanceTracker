#!/bin/bash
csvFile=$1
sqliteFile=$2
processedCsv="$csvFile.processed"

cut -d ',' -f 2,3,4 $csvFile | tail -n +2 > $processedCsv

upsertStatement="INSERT INTO students (email, name, grad_year) VALUES "

while read -r line; do
    email=$(echo $line | cut -d ',' -f 1)
    name=$(echo $line | cut -d ',' -f 2)
    yog=$(echo $line | cut -d ',' -f 3)
    upsertStatement="$upsertStatement (\"$email\",\"$name\",$yog),"
done < $processedCsv

upsertStatement=$(echo $upsertStatement | sed 's/,$//g')
upsertStatement="$upsertStatement ON CONFLICT (email) DO NOTHING;"

echo -e "Executing statement:\n $upsertStatement\n on database: $sqliteFile"

sqlite3 $sqliteFile "$upsertStatement" "SELECT count(*) from students;" ".exit"
rm -f $processedCsv