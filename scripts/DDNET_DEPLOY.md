# DDNet Cloud Deploy

This workflow is designed for your current setup:

- Local source: `D:/Desktop/AI/newfuwq/f/ddnet-src`
- Local Windows test binary: `D:/Desktop/AI/newfuwq/f/build-ddnet-server-vs2026/Release/DDNet-Server.exe`
- Ubuntu source dir: `/home/ubuntu/ddnet-src`
- Ubuntu build dir: `/home/ubuntu/ddnet-build-server`
- Ubuntu runtime dir: `/home/ubuntu/ddnet-server`

## What the script does

1. Checks that your local DDNet source exists.
2. Checks that your local Windows server binary exists.
3. Packs the full source tree into a `.tar.gz` archive.
4. Uploads that archive to the Ubuntu server.
5. Verifies the archive SHA256 on the server before extracting it.
6. Extracts to a temporary source directory on Ubuntu.
7. Runs the Linux `game-server` build from that temporary source tree.
8. Replaces `/home/ubuntu/ddnet-src` only after the build succeeds.
9. Replaces `/home/ubuntu/ddnet-server/DDNet-Server` only if you explicitly request install mode.
10. Restarts `ddnet` only if you explicitly request restart mode.

## Safety behavior

- If the remote build fails, the current runtime server binary is not touched.
- If the remote build fails, the current `/home/ubuntu/ddnet-src` is not replaced.
- Before the source directory is replaced, the old one is moved into:
  `/home/ubuntu/ddnet-deploy/backups/`
- Before the runtime binary is replaced, the old one is copied into:
  `/home/ubuntu/ddnet-deploy/backups/`

## Recommended entry script

The easiest entrypoint is:

`D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.bat`

You can double-click it directly, or run it from `cmd`.

It will open a simple menu:

- `1` only uploads and compiles on the cloud
- `2` uploads, compiles, replaces the runtime server, and restarts `ddnet`
- `Q` exits

The PowerShell entrypoint still exists here:

`D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.ps1`

The real local config file is intentionally not meant to be committed.
The repo-safe template is:

`D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.config.example.json`

## Commands

Open the `.bat` menu:

```bat
D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.bat
```

Open the PowerShell menu:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.ps1
```

Run mode 1 directly without the menu:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.ps1 -Mode build
```

Run mode 2 directly without the menu:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Desktop\AI\newfuwq\f\ddnet-src\scripts\ddnet_deploy.ps1 -Mode release
```

## Password input

By default the script asks for the SSH password interactively.

If you want to avoid retyping it for one PowerShell session:

```powershell
$env:DDNET_DEPLOY_PASSWORD = "your-password"
```

Then run the deploy command in the same PowerShell window.

## Recommended workflow

1. Change code locally.
2. Build and test locally first.
3. Run the deploy script without `-InstallRuntime`.
4. Confirm the Linux cloud build passes.
5. Run mode 2 when you want to go live.
