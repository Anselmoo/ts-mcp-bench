
cd /tmp/tsbench-run-tsr9v_05 && python - <<'EOF'
s=open('ts.py').read()
s=s.replace("""        out.append((np.trace(V.T@H0@V)/deg/B,'%d%s'%(mult,lab)))""","""        E=np.trace(V.T@H0@V)/deg/B
        chi2=np.real(np.sum(np.conj(V)*((C4**2)[:,None]*V)))/mult
        if od==3 and abs(chi2-3)<1e-3: out+= [(E,'%dA1g'%mult),(E,'%dEg'%mult)]
        elif od==3 or od in(1,2): out.append((E,'%d%s'%(mult,lab)))
        else: out.append((E,'%d?od%d_c%.2f_c2%.2f'%(mult,od,chi,chi2)))""")
open('ts.py','w').write(s)
EOF
python ts.py 2>&1 | tail -10; sha256sum diagram.png; cat res.json