#!/bin/bash

set -euo pipefail

RR_PROJECT_ROOT=/opt/raconteur
PROJECT_ROOT=/opt/much
CONDA_ROOT=/opt/conda

DATASET_ROOT=$PROJECT_ROOT/assets/patch
RR_DATASET_ROOT=$RR_PROJECT_ROOT/assets/auch

LOG_ROOT=$PROJECT_ROOT/assets/logs
LOG_FILE=$LOG_ROOT/alternate.txt

if test ! -d $LOG_ROOT; then
  mkdir $LOG_ROOT
fi

if test ! -d $DATASET_ROOT; then
  echo Dataset root $DATASET_ROOT does not exist. Exiting.
  exit 1
fi

. "$CONDA_ROOT/etc/profile.d/conda.sh"
. /home/zeio/bashrc/creds/personal.sh

if test -f $LOG_FILE; then
  echo '' >> $LOG_FILE
fi

date +"%Y-%m-%d %H:%M:%S" >> $LOG_FILE

cd $PROJECT_ROOT

conda run -n raconteur --no-capture-output python -m much alternate \
  $RR_DATASET_ROOT/index.txt \
  $DATASET_ROOT/threads \
  $RR_DATASET_ROOT/threads \
  --artist-one xenia \
  --artist-two baya \
  --poster-root $DATASET_ROOT/media \
  --interactive 1>> $LOG_FILE 2>&1
