#!/usr/bin/env python3
import time
from unknown_consumers import collect_meter_power

if len(collect_meter_power(time.time() - 30)) > 0:
    print("tibber pulse is OK.")
    exit(0)
else:
    print("no data from tibber pulse.")
    exit(1)
