#!/bin/bash

# kill -9 $(lsof -ti :8000)

# Caminho absoluto para o projeto (ajuste conforme necessário)
PROJECT_DIR=/home/thais/Desktop/mmcloud_agent

# Ativar ambiente virtual
cd $PROJECT_DIR
source ./venv/bin/activate

# Rodar Python em background
python websocket_obd_rasp.py &

# Esperar
sleep 2

# Rodar Electron
$PROJECT_DIR/2.2.0/linux-arm64-unpacked/electron-vite-react &
