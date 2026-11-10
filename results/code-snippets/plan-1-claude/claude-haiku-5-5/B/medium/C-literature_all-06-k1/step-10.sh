
W=$(ls -d /dev/shm/d3* | head -1); cd $W 2>/dev/null || { echo nodir; }; ls
