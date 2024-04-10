param (
    [Parameter(Mandatory = $false)]
    [switch]$Dev
)

####################################################################

function Remove-Folders {
    param (
        [Parameter(Mandatory=$true)]
        [string[]]$Paths
    )

    foreach ($Path in $Paths) {
        if (Test-Path $Path) {
            Write-Output "Removing $Path..."
            Remove-Item -Path $Path -Recurse -Force
        } else {
            Write-Output "Skipping $Path as it does not exist."
        }
    }
}

####################################################################
Write-Output "Please ensure you have valid icon.ico in src\waker\assets\"
Write-Output "You can create one using https://www.icoconverter.com/ or https://icoconvert.com/"
Write-Output "Building Waker..."
$EnvName = "prod_venv"
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Output "Cleaning Up..."
Remove-Folders -Paths @(".\dist", ".\build", ".\$EnvName")

Write-Output "Building..."

Write-Output "Creating Virtual Environment..."
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements-dev.txt
.\venv\Scripts\python.exe -m venv $EnvName

Write-Output "Activating Virtual Environment..."
$ActivateScript = Join-Path -Path ".\" -ChildPath "$EnvName\Scripts\Activate.ps1"
. $ActivateScript

Write-Output "Installing Dependencies..."
& .\$EnvName\Scripts\python.exe -m pip install --upgrade pip
& .\$EnvName\Scripts\pip.exe install -r requirements.txt
& .\$EnvName\Scripts\pip.exe install -r .\src\core\requirements.txt

Write-Output "Building Executable..."

$InstallerArgsDebug = @(
    "--noconsole",
    "--add-data",
    ".\src\waker\assets\*.png;.\assets",
    "--add-data",
    ".\src\waker\assets\*.ico;.\assets",
    "--add-data",
    ".\src\waker\assets\*.json;.\assets",
    "--collect-data",
    "sv_ttk",
    "--paths",
    ".\src",
    "--clean",
    "--icon",
    ".\src\waker\assets\icon.ico",
    "--name",
    "Rekaw",
    ".\src\waker\main.py"
)

$InstallerArgs = $InstallerArgsDebug + @(
    "--log-level",
    "WARN",
    "--onefile"
)

if ($Dev)
{
    & .\$EnvName\Scripts\pyinstaller.exe $InstallerArgsDebug
}
else
{
    & .\$EnvName\Scripts\pyinstaller.exe $InstallerArgs
}

if ($Dev)
{
    Write-Output "Debug mode enabled, skipping compression..."
    & .\dist\Rekaw\Rekaw.exe
}
else
{
    Write-Output "Creating Version File..."
    & .\venv\Scripts\create-version-file.exe metadata.yml --outfile file_version_info.txt

    Write-Output "Setting Version..."
    & .\$EnvName\Scripts\pyi-set_version.exe ./file_version_info.txt ./dist/Rekaw.exe

    Write-Output "Compressing Files..."
    Compress-Archive -Path .\dist\Rekaw.exe -DestinationPath .\dist\Rekaw.zip
}

Write-Output "Done!"