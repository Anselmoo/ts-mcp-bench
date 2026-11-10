python3 - <<'EOF'
s=open('ts.py').read()
s=s.replace("""        lab={(1,1)""","""        chi2=np.real(np.sum(np.abs(vs)**2*(phase**2)[:,None]))
        w0=np.linalg.eigvalsh(H2)
        en=w[i] if dqB>0 else w0[np.argmin(abs(w0-np.trace(vs.T@H2@vs)/dim))]
        if dim==3 and round(chi2)==3:
            out.append((en,f"{int(round(2*S+1))}A1g")); out.append((en,f"{int(round(2*S+1))}Eg")); i=j; continue
        lab={(1,1)""")
s=s.replace("        en=w[i] if dqB>0 else np.trace(vs.T@H2@vs)/dim\n","")
open('ts.py','w').write(s)
EOF
MPLCONFIGDIR=<SANDBOX_TMP>/mpl python3 ts.py; sha256sum diagram.png; cat res.json