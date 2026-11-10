
cd <SANDBOX_TMP>; sed -i 's/apply(D,(s,r),(q,p))/apply(D,(r,s),(q,p))/' d7.py; python3 t.py; python3 d7.py
