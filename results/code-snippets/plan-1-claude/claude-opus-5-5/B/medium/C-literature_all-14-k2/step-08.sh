
D=$TMPDIR/co7q; cd $D && sed -i 's/\*np.sqrt(4/*(-1)**m1*np.sqrt(4/' d7.py && python3 - << 'EOF'
s=open('d7.py').read()
s=s.replace("""                i=l.index(s_); sg*=(-1)**i; l.pop(i)
                i=l.index(r_); sg*=(-1)**i; l.pop(i)""","""                i=l.index(r_); sg*=(-1)**i; l.pop(i)
                i=l.index(s_); sg*=(-1)**i; l.pop(i)""")
open('d7.py','w').write(s)
EOF
grep -n "m1\*np" d7.py; python3 fit.py
