
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > fit3.py
exec(open('scan.py').read().split('best=None')[0].replace('print(groups((715,1000,4000)))',''))
for Dq in [715]:
  for B in range(700,1100,50):
    v,m=groups((Dq,B,4*B)); print(Dq,B,m, (v[1:]-v[0]).round(0))
# solve B for nu2 = 15200 at Dq=715
from scipy.optimize import brentq
f=lambda B: (groups((715,B,4*B))[0][2]-groups((715,B,4*B))[0][0])-15200
Bs=brentq(f,600,1200); print("B from nu2",Bs, groups((715,Bs,4*Bs))[0]-groups((715,Bs,4*Bs))[0][0])
EOF
python3 fit3.py 2>&1 | tail -12
