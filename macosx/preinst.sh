#!/usr/bin/env bash

PLIST="/Library/LaunchDaemons/io.pokesec.epcontrol.plist"

if [ -f "$PLIST" ];
then
    sudo launchctl unload "$PLIST";
    sudo rm -f "$PLIST";
fi