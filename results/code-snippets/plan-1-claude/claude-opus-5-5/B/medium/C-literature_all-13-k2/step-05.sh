
cd $TMPDIR && sed -i 's/round(e-E0,1)/e-E0/; s/least_squares(res,\[805,850,3800\])/least_squares(res,[805,850,3800],diff_step=1e-4)/' d7.py && python3 d7.py | tail -2
