
cd $TMPDIR && sed -i 's/g=L\[0\]\[0\]; assert L\[0\]\[2\]<1/D=[x[0] for x in L if x[2]<1]; g=D[0]/; s/d=\[x\[0\]-g for x in L\[1:\] if x\[2\]<1\]/d=[x-g for x in D[1:]]/' fit.py && python3 fit.py
