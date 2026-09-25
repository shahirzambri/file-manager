#!/bin/bash
echo "Starting File Manager..."
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 2
python3 ~/Desktop/FileSorter/file_manager_ui.py &
echo "Waiting for server..."
for i in $(seq 1 20); do
    sleep 1
    if curl -s http://localhost:8765 > /dev/null 2>&1; then
        echo "Server ready!"
        open http://localhost:8765
        wait
        exit 0
    fi
done
echo "Server did not start."
