#!/bin/bash

conda create -n much python=3.11.5
conda activate much

conda install requests pandas click tqdm python-lsp-server beautifulsoup4
