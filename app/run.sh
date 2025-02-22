#!/bin/bash

echo "Frontend Started..."
python3 /app/run.py &
echo "Scheduler Started..."
python3 /app/scheduler/scheduler.py &
echo "Both are running..."


wait
echo "Still running..."
