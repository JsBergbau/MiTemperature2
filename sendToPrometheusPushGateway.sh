#!/usr/bin/bash

captors="A4:C1:38:0B:F8:E1 cave_garage
A4:C1:38:1E:8E:43 escalier_sous_sol
A4:C1:38:5D:FB:DC salle_de_bain
A4:C1:38:6F:1D:80 salon
A4:C1:38:78:6D:F6 cave_bureau
A4:C1:38:9C:E3:70 chambre_verte
A4:C1:38:BB:54:29 cave_buanderie
A4:C1:38:CF:FD:78 chambre_bleue"

while :; do
echo "$captors" | while read captor; do
  # python3 ./LYWSD03MMC.py --device ${captor% *} --round --debounce -c 1
  timeout -k 5 30 python3 ./LYWSD03MMC.py --device ${captor% *} --round --debounce -call ./prometheus/sendToPrometheus.py -n ${captor#* } -c 1 -urc 1
done
done
