#!/bin/bash

set -euo pipefail

conda create -n much 'python<3.13' -y

conda run -n much --no-capture-output pip install requests
conda run -n much --no-capture-output pip install beautifulsoup4
conda run -n much --no-capture-output pip install numpy
conda run -n much --no-capture-output pip install click
conda run -n much --no-capture-output pip install pandas
conda run -n much --no-capture-output pip install tqdm
conda run -n much --no-capture-output pip install flask
conda run -n much --no-capture-output pip install torch torchvision torchaudio
conda run -n much --no-capture-output pip install scipy
conda run -n much --no-capture-output pip install ipython
conda run -n much --no-capture-output pip install pydub
conda run -n much --no-capture-output pip install music-tag
conda run -n much --no-capture-output pip install num2words
conda run -n much --no-capture-output pip install transliterate
conda run -n much --no-capture-output pip install kokoro
conda run -n much --no-capture-output pip install google-images-search

git submodule update --init

sudo bash -c 'apt-get update && apt-get install ffmpeg -y'
