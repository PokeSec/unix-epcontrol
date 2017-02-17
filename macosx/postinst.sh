#!/usr/bin/env bash

PLIST="/Library/LaunchDaemons/io.pokesec.epcontrol.plist"

if [ -f "$PLIST" ];
then
    sudo launchctl load "$PLIST";
fi