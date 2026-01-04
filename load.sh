#!/bin/bash

set -euo pipefail

PROJECT_ROOT=/opt/much
CONDA_ROOT=/opt/conda

DATASET_ROOT=$PROJECT_ROOT/assets/patch

LOG_ROOT=$PROJECT_ROOT/assets/logs
LOG_FILE=$LOG_ROOT/load.txt

if test ! -d $LOG_ROOT; then
  mkdir $LOG_ROOT
fi

if test ! -d $DATASET_ROOT; then
  mkdir $DATASET_ROOT
fi

. "$CONDA_ROOT/etc/profile.d/conda.sh"

if test -f $LOG_FILE; then
  echo -e '\n' >> $LOG_FILE
fi

date +"%Y-%m-%d %H:%M:%S" >> $LOG_FILE

cd $PROJECT_ROOT
conda run -n much --no-capture-output python -m much load -i $DATASET_ROOT/index.tsv -r $DATASET_ROOT/media -p $DATASET_ROOT/threads 1>> $LOG_FILE 2>&1
