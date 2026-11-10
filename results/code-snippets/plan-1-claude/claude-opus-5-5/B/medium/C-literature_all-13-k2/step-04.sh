
cd $TMPDIR && sed -i 's/\*(2\*l+1)\*gaunt/*gaunt/; s|F4=C/35; F2=B+5\*F4|F4=441*C/35/441*441/441; F4=441*(C/35); F2=49*(B+5*C/35)|' d7.py && grep -n "F4=" d7.py && python3 d7.py
