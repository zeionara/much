#!/bin/bash

set -euo pipefail

RR_PROJECT_ROOT=/opt/raconteur
PROJECT_ROOT=/opt/much
VENV_ROOT=/opt/marude/.venv

DATASET_ROOT=$PROJECT_ROOT/assets/patch
RR_DATASET_ROOT=$RR_PROJECT_ROOT/assets/auch

LOG_ROOT=$PROJECT_ROOT/assets/logs
LOG_FILE=$LOG_ROOT/alternate.txt

export PYTHONUNBUFFERED=True

if test ! -d $LOG_ROOT; then
  mkdir $LOG_ROOT
fi

if test ! -d $DATASET_ROOT; then
  echo Dataset root $DATASET_ROOT does not exist. Exiting.
  exit 1
fi

. /home/zeio/.oh-my-zsh/custom/bashrc/creds/personal.sh

if test -f $LOG_FILE; then
  echo >> $LOG_FILE
fi

date +"%Y-%m-%d %H:%M:%S" >> $LOG_FILE

cd $PROJECT_ROOT

$VENV_ROOT/bin/python -m much alternate \
  $RR_DATASET_ROOT/index.txt \
  $DATASET_ROOT/threads \
  $RR_DATASET_ROOT/threads \
  --artist-one xenia \
  --artist-two baya \
  --poster-root $DATASET_ROOT/media \
  --interactive 1>> $LOG_FILE 2>&1
