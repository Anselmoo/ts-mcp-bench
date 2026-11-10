
cd <SANDBOX_TMP>; sed -i "s/^for drop in obs:/obs={'4T2(1)':8480,'4A2(1)':16305,'4T1(2)':20360,'2T1(2)':21001}\nfor drop in obs:/" t.py; python3 t.py 2>&1 | tail -4
