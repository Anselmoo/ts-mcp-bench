cd $TMPDIR && python3 - << 'EOF'
s=open('d5.py').read()
s=s.replace("""                    k=lst.index(q);sg*=(-1)**k;lst.pop(k)
                    k=lst.index(p);sg*=(-1)**k;lst.pop(k)""","""                    k=lst.index(p);sg*=(-1)**k;lst.pop(k)
                    k=lst.index(q);sg*=(-1)**k;lst.pop(k)""")
open('d5.py','w').write(s)
EOF
python3 d5.py