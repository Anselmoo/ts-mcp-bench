cd <SANDBOX_TMP>/tmp.gIlMPjOlU8 && cat >> t2g.py << 'EOF'

for F2,F4 in [(1.0,0.0),(0.0,1.0)]:
    H=build({0:0.0,2:F2,4:F4}).astype(complex)
    Ht=Qb.conj().T@H@Qb
    S2t=Qb.conj().T@S2()@Qb
    w,v=np.linalg.eigh(Ht+1e3*S2t)
    cnt=collections.Counter()
    for i in range(len(w)):
        x=v[:,i]; s=round((x.conj()@S2t@x).real,2); e=round((x.conj()@Ht@x).real,5)
        cnt[(s,e)]+=1
    print(F2,F4,dict(cnt))
EOF
python3 t2g.py | tail -2