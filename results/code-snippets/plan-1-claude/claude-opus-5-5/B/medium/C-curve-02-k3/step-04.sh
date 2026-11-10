
cd $TMPDIR && python3 - << 'EOF'
s=open('d3.py').read()
s=s.replace("""                    i=l.index(q); sgn*=(-1)**i; l.pop(i)
                    i=l.index(p); sgn*=(-1)**i; l.pop(i)""","""                    i=l.index(p); sgn*=(-1)**i; l.pop(i)
                    i=l.index(q); sgn*=(-1)**i; l.pop(i)""")
open('d3.py','w').write(s)
EOF
python3 d3.py
