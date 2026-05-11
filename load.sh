#!/bin/bash

set -euo pipefail

PROJECT_ROOT=/opt/much
VENV_ROOT=/opt/marude/.venv

DATASET_ROOT=$PROJECT_ROOT/assets/patch

LOG_ROOT=$PROJECT_ROOT/assets/logs
LOG_FILE=$LOG_ROOT/load.txt

export PYTHONUNBUFFERED=True

if test ! -d $LOG_ROOT; then
  mkdir $LOG_ROOT
fi

if test ! -d $DATASET_ROOT; then
  echo 'Dataset root folder does not exist'
  exit 1
fi

if test -f $LOG_FILE; then
  echo >> $LOG_FILE
fi

date +"%Y-%m-%d %H:%M:%S" >> $LOG_FILE

cd $PROJECT_ROOT
$VENV_ROOT/bin/python -m much load -i $DATASET_ROOT/index.tsv -r $DATASET_ROOT/media -p $DATASET_ROOT/threads 1>> $LOG_FILE 2>&1
