#!/bin/sh
#
# Script to run in background svxbridge.py 
#
# a tester manuellement et adapter les ports et les output input device 
# si quelqu'un parle sur la ROOM ca ne marche pas donc a relancer a la main
python /opt/svxbridge/svxbridge.py > /dev/null 2>&1 &

