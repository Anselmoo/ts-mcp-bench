
cd /tmp && d=$(ls -dt /tmp/tmp* | head -1); cd $d; sed -i 's/\*(2\*l+1)\*gaunt/*gaunt/' d3.py; python3 d3.py