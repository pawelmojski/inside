#!/bin/bash
# RDP Backend wrapper - PyRDP MITM on localhost
# This runs behind rdp_guard.py which handles access control

LISTEN_IP="127.0.0.1"
LISTEN_PORT="13389"
TARGET_SERVER="10.30.0.140"
RECORDINGS_DIR="/var/log/jumphost/rdp_recordings"
PYRDP_MITM="/opt/jumphost/venv/bin/pyrdp-mitm"

echo "Starting PyRDP MITM backend..."
echo "Listen: ${LISTEN_IP}:${LISTEN_PORT} (behind guard proxy)"
echo "Target: ${TARGET_SERVER}:3389"
echo "Recordings: ${RECORDINGS_DIR}"

# Start pyrdp-mitm on localhost (access control done by rdp_guard.py)
exec ${PYRDP_MITM} \
    -a ${LISTEN_IP} \
    -l ${LISTEN_PORT} \
    -o ${RECORDINGS_DIR} \
    ${TARGET_SERVER}
