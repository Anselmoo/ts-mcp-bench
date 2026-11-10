
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > run2.py
exec(open('run.py').read().split('o=spectrum(1,0,0)')[0])
def uniq(a):
    vals=[];mult=[]
    for x in a:
        if vals and abs(x-vals[-1])<1e-5: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    return list(zip(np.round(vals,3),mult))
import sys
for p in [(1,0,0),(0,1,0),(0,0,1),(0.7,1,4)]:
    o=spectrum(*p)
    print(p,'Q',uniq(o[1.5]),'D',uniq(o[0.5]))
EOF
python3 run2.py 2>&1 | tail -6
