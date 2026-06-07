# DDNet Local Server Build And Run

Use this file when you changed source code and want to rebuild and start your local Windows server:

`D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_local_build_and_run.bat`

## What it does

1. Checks whether your local runtime folder exists.
2. Stops the previous local `DDNet-Server.exe` if it is still running from your local runtime folder.
3. Rebuilds the local server from:
   `D:\Desktop\AI\newfuwq\f\build-ddnet-server-vs2026`
4. Copies the newly built files into:
   `D:\Desktop\AI\newfuwq\f\ddnet-server\DDNet-19.7.1-win64`
5. Starts the local server in a new window.

## Files it refreshes

- `DDNet-Server.exe`
- `libcurl.dll`
- `sqlite3.dll`
- `z.dll`

## Notes

- Your local server config is still read from:
  `D:\Desktop\AI\newfuwq\f\ddnet-server\DDNet-19.7.1-win64\data\autoexec_server.cfg`
- If compilation fails, the script will stop and the server will not be started.
- If the old local server is still open, the script will close that local server process first.
