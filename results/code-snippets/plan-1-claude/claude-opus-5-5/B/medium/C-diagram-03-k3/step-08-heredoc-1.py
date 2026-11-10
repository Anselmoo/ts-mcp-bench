s=open('ts.py').read()
s=s.replace("""def levels(dqB):
    H=H2+H1*(dqB+1e-5)*B""","""def levels(dqB):
    H=H2+H1*(dqB if dqB>0 else 0.02)*B""")
s=s.replace("""        out.append((w[i],""","""        en=w[i] if dqB>0 else np.trace(vs.T@H2@vs)/dim
        out.append((en,""")
s=s.replace("w[j]-w[i]<1e-3","w[j]-w[i]<1e-6")
open('ts.py','w').write(s)
