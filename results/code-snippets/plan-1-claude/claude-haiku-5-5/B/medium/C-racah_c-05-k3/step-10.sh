
sed -i 's/3\*Z\*\*2-(X\*\*2+Y\*\*2)/3*Z**2-1.0/' d3.py && grep -n "funcs=" d3.py && python3 dbg2.py 2>&1 | tail -4
