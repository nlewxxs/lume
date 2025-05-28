# Simulate the software locally
sudo env LUME_RUN_MODE=deploy LUME_CONTROLLER_IP=127.0.0.1 LUME_VERBOSE=false docker compose up --build --force-recreate
