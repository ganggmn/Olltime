#!/bin/bash
# 250m 생활인구 zip에서 올림픽공원 16칸만 뽑아요(audience_demo.py용). data 폴더에서 bash ../analysis/grid_extract.sh
mkdir -p ~/grid; printf "%s\n" 66004650 66004675 66254625 66254650 66254700 66504625 66504650 66504675 66504700 66504725 66754650 66754675 67004625 67004650 67004675 67254625 > ~/grid/cells.txt
for z in livingpop/250_LOCAL_RESD_2025*.zip; do m=$(basename $z .zip | sed s/250_LOCAL_RESD_//); [ -s ~/grid/$m.csv ] && continue; unzip -p "$z" | LC_ALL=C grep -F -f ~/grid/cells.txt | iconv -f cp949 -t utf-8 -c > ~/grid/$m.csv; done
