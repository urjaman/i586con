#!/bin/sh
# In case you need to drop a couple of mp3s onto the CD for like,
# hardware demonstration purposes... you could run this and have
# a couple of selected Demo competition songs :)
# IANAL, I dunno about their licensing, but atleast they're
# free to download from files.scene.org... I expect no complaints :P

mkdir -p mp3
cd mp3
# Use youtube just as a convenient (not really...) media storage platform :P
DL="youtube-dl -x --audio-format mp3 --audio-quality 192K"

# War Against the Machines by Paavo "Tarantula" Härkönen
$DL https://youtu.be/uycimsN8AgY
# Very serious problems (Internet has problems) by la_mettrie/tsoi
$DL https://www.youtube.com/watch?v=tcSIuAua84U
# Matka osoiteavaruuteen by la_mettrie
$DL https://youtu.be/qDB_RTOEplw
# Florida Man by Florida Man
$DL https://youtu.be/utMDs48tDec
# The Way That Leads to You by HBR & Mari
$DL https://youtu.be/QvH81aTxWvg
