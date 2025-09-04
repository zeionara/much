#!/bin/bash

# python -m much filter -s 905500 -i assets/index.tsv -n 1000
# python -m much filter -t 20 -s 863560 -i assets/index.tsv -n 1000
# python -m much filter -t 20 -s 804660 -i assets/index.tsv -n 100
# python -m much filter -t 20 -s 784940 -i assets/index.tsv -n 1000
python -m much filter -t 20 -i assets/index.tsv -n 10000 -s 461040
