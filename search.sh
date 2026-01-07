#!/bin/bash

for id in $(cat assets/patch/index.tsv | grep -i "$1" | cut -d "	" -f1); do
    filename=$(find assets/patch/threads -name $id.txt)

    echo $filename $(cat $filename | wc -l)
    head -n 1 $filename
    echo
done
