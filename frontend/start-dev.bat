@echo off
set npm_config_cache=D:\B_Projects\Job_Orchestrator\frontend\.npm-cache
set npm_config_update_notifier=false
cd /d D:\B_Projects\Job_Orchestrator\frontend
set PORT=3001
node node_modules\next\dist\bin\next -p 3001
