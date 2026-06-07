param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "ddnet_deploy.config.json"),
    [ValidateSet("menu", "build", "release")]
    [string]$Mode = "menu",
    [switch]$InstallRuntime,
    [switch]$RestartService,
    [switch]$SkipLocalBuildCheck,
    [int]$BuildJobs = 2
)

function Show-ModeMenu {
    Write-Host ""
    Write-Host "================ DDNet 云端部署 ================" -ForegroundColor Cyan
    Write-Host "1. 只上传并云端编译（不替换线上服务器）" -ForegroundColor Yellow
    Write-Host "2. 上传并云端编译，然后替换线上服务器并重启" -ForegroundColor Yellow
    Write-Host "Q. 退出" -ForegroundColor DarkGray
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""

    while($true) {
        $choice = (Read-Host "请选择模式").Trim().ToUpperInvariant()
        switch($choice) {
            "1" { return "build" }
            "2" { return "release" }
            "Q" { return "quit" }
            default {
                Write-Host "输入无效，请输入 1、2 或 Q。" -ForegroundColor Red
            }
        }
    }
}

function Resolve-DeployMode {
    param(
        [string]$RequestedMode,
        [bool]$RequestedInstallRuntime,
        [bool]$RequestedRestartService
    )

    if($RequestedRestartService -and -not $RequestedInstallRuntime) {
        throw "参数错误：-RestartService 必须和 -InstallRuntime 一起使用。"
    }

    if($RequestedMode -ne "menu") {
        return $RequestedMode
    }

    if($RequestedInstallRuntime -or $RequestedRestartService) {
        return "release"
    }

    return Show-ModeMenu
}

function Invoke-Deploy {
    param(
        [string]$SelectedMode
    )

    $pythonCommand = Get-Command python -ErrorAction Stop
    $scriptPath = Join-Path $PSScriptRoot "ddnet_deploy.py"

    $arguments = @(
        $scriptPath,
        "--config", $ConfigPath,
        "--build-jobs", $BuildJobs
    )

    if($SkipLocalBuildCheck) {
        $arguments += "--skip-local-build-check"
    }

    switch($SelectedMode) {
        "build" {
            Write-Host ""
            Write-Host "当前模式：只上传并云端编译，不替换线上服务器。" -ForegroundColor Cyan
        }
        "release" {
            $arguments += "--install-runtime"
            $arguments += "--restart-service"
            Write-Host ""
            Write-Host "当前模式：上传、云端编译、替换线上服务器并重启服务。" -ForegroundColor Cyan
        }
        default {
            throw "未知模式：$SelectedMode"
        }
    }

    Write-Host "配置文件：$ConfigPath" -ForegroundColor DarkGray
    Write-Host "构建并行数：$BuildJobs" -ForegroundColor DarkGray
    Write-Host ""

    & $pythonCommand.Source @arguments
}

try {
    $selectedMode = Resolve-DeployMode -RequestedMode $Mode -RequestedInstallRuntime $InstallRuntime.IsPresent -RequestedRestartService $RestartService.IsPresent
    if($selectedMode -eq "quit") {
        Write-Host "已取消，本次没有执行部署。" -ForegroundColor Yellow
        exit 0
    }

    Invoke-Deploy -SelectedMode $selectedMode
    $exitCode = $LASTEXITCODE

    Write-Host ""
    if($exitCode -eq 0) {
        switch($selectedMode) {
            "build" {
                Write-Host "结果：云端编译成功。" -ForegroundColor Green
                Write-Host "说明：线上正在运行的服务器没有被替换，你可以先继续检查再决定是否上线。" -ForegroundColor Green
            }
            "release" {
                Write-Host "结果：云端编译成功，线上服务端已替换并已执行重启。" -ForegroundColor Green
                Write-Host "说明：脚本已验证服务重启流程通过。" -ForegroundColor Green
            }
        }
    }
    else {
        switch($selectedMode) {
            "build" {
                Write-Host "结果：云端编译失败，线上服务器没有被替换。" -ForegroundColor Red
            }
            "release" {
                Write-Host "结果：部署失败。" -ForegroundColor Red
                Write-Host "说明：如果失败发生在编译阶段，线上运行中的服务器不会被替换。" -ForegroundColor Red
            }
        }
        Write-Host "请直接看上面日志最后几十行，里面会有具体报错原因。" -ForegroundColor Yellow
    }

    exit $exitCode
}
catch {
    Write-Host ""
    Write-Host "脚本没有开始执行：" -ForegroundColor Red -NoNewline
    Write-Host " $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
