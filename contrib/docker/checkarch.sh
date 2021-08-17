#!/bin/sh

if [ "`uname -m`" = "armv7l" ]; then
  echo "y"
  exit 0
fi

echo "n"
exit 0
