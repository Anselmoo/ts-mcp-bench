time python3 -c "
import irr
for row in irr.analyze(0,780,3500):
    if row[0]=='D' and row[1]<30000: print(row[1],row[2],row[3])
"