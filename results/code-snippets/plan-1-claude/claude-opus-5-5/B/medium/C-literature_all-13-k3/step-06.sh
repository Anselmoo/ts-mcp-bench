
cd <SANDBOX_TMP>; python3 -c "
exec(open('fit.py').read().split('obs=')[0])
for e,l in levels(800,800,3200)[:16]: print(round(e),l)
"
