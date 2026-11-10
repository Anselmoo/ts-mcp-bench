
cd "$(pwd)" && sed -i 's/(s1,q),(s2,d)=levels(Dq,B,C)/(s1,d),(s2,q)=levels(Dq,B,C)/' run.py && python3 run.py 2>&1 | tail -4
