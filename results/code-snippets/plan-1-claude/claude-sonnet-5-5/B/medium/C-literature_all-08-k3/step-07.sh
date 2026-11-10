cd <SANDBOX_TMP> && python3 - <<'E'
s=open('a.py').read()
s=s.replace("            s,nd=apply([('c',a),('a',b)],det)\n","            if orbs[a][1]!=orbs[b][1]: continue\n            s,nd=apply([('c',a),('a',b)],det)\n")
s=s.replace("        s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)","        if orbs[a][1]!=orbs[cc][1] or orbs[b][1]!=orbs[d][1]: continue\n        s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)")
open('a.py','w').write(s)
E
python3 a.py