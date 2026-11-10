cat << 'EOF' > run2.py
import pickle
res=pickle.load(open('res.pkl','rb'))
for k in sorted(res):
    L=res[k]
    print(k, len(L))
    print('   ', [(t,round(e,3)) for t,e in L[:8]])
EOF
python3 run2.py