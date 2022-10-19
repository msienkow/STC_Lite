# Installer for SaniTrend™ Cloud Lite
Add-Type -AssemblyName PresentationCore,PresentationFramework

# Set Execution Policy for Powershell Scripts
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser


# Download Github Respoitory
function DownloadGitHubRepository 
{ 
    param( 
       [Parameter(Mandatory=$False)] 
       [string] $Name, 
        
       [Parameter(Mandatory=$False)] 
       [string] $Author, 
        
       [Parameter(Mandatory=$False)] 
       [string] $Branch = "main", 
        
       [Parameter(Mandatory=$False)] 
       [string] $Location = "c:\temp" 
    ) 
    
    # Force to create a zip file 
    $ZipFile = "$location\SaniTrendCloud.zip" 
    New-Item $ZipFile -ItemType File -Force
    
    $RepositoryZipUrl = "https://github.com/msienkow/STC_Lite/archive/refs/heads/main.zip"

    # download the zip 
    Write-Host 'Downloading SaniTrend Cloud Lite from Github. Please wait...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-RestMethod -Uri $RepositoryZipUrl -OutFile $ZipFile
    Write-Host 'Download finished'

    #Extract Zip File
    Write-Host 'Starting unziping the GitHub Repository locally'
    Expand-Archive -Path $ZipFile -DestinationPath $location -Force
    Write-Host 'Unzip finished'
    
    # remove zip file
    Remove-Item -Path $ZipFile -Force 
}

# Download Thingworx Edge Microserver from Thingworx File Repository
function DownloadMicroServer
{ 
    param( 
       [Parameter(Mandatory=$False)] 
       [string] $Name, 
        
       [Parameter(Mandatory=$False)] 
       [string] $Author, 
        
       [Parameter(Mandatory=$False)] 
       [string] $Branch = "main", 
        
       [Parameter(Mandatory=$False)] 
       [string] $Location = "c:\temp" 
    ) 
    
    # Force to create a zip file 
    $ZipFile = "$location\microserver.zip" 
    New-Item $ZipFile -ItemType File -Force

    $RepositoryZipUrl = $serverDownload

    # download the zip 
    Write-Host 'Downloading Edge Microserver. Please wait...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-RestMethod -Uri $RepositoryZipUrl -OutFile $ZipFile
    Write-Host 'Download finished'

    #Extract Zip File
    Write-Host 'Starting unzipping Edge Microserver...'
    Expand-Archive -Path $ZipFile -DestinationPath $location -Force
    Write-Host 'Unzip finished'
    
    # remove zip file
    Remove-Item -Path $ZipFile -Force 
}

Write-Host ""
Write-Host ""
Write-Host ""
Write-Host ""
Write-Host ""
Write-Host ""
Write-Host ""
Write-Host " ____              _ _____                   _    ____ _                 _ "
Write-Host "/ ___|  __ _ _ __ (_)_   _|___ ___ _ __   __| |  / ___| | ___  _   _  __| |"
Write-Host "\___ \ / _  |  _ \| | | ||  __/ _ \  _ \ / _  | | |   | |/ _ \| | | |/ _  |"
Write-Host " ___) | (_| | | | | | | || | |  __/ | | | (_| | | |___| | (_) | |_| | (_| |"
Write-Host "|____/ \__,_|_| |_|_| |_||_|  \___|_| |_|\__,_|  \____|_|\___/ \__,_|\__,_|"
Write-Host ""
Write-Host ""
Write-Host ""
$wshell = New-Object -ComObject Wscript.Shell
$answer = $wshell.Popup("Do you want to install SaniTrend Cloud?",0,"SaniTrend Cloud Installer",64+4)

if ($answer -eq 6) {
    # Get SMI Number from user
    Clear-Host
    $choices  = '&Yes', '&No'
    $loop = $true
    DO {
        Clear-Host
        $SMINumber = Read-Host -Prompt 'Please Enter the SMI Number: '
        Clear-Host
        $title    = ''
        $question = 'Is ' + $SMINumber + ' the correct SMI number?'
        $decision = $Host.UI.PromptForChoice($title, $question, $choices, 0)
        if ($decision -eq 0) {
            $loop = $False
        }
    } While ($loop)

    # Get PLC IP Address
    Clear-Host
    $loop = $true
    DO {
        Clear-Host
        $PLCIP = Read-Host -Prompt 'Please enter the PLC IP Address: '
        Clear-Host
        $title    = ''
        $question = 'Is ' + $PLCIP + ' the correct PLC IP Address?'
        $decision = $Host.UI.PromptForChoice($title, $question, $choices, 0)
        if ($decision -eq 0) {
            $loop = $False
        }
    } While ($loop)

    # Get Application Key
    Clear-Host
    $loop = $true
    DO {
        Clear-Host
        $applicationKey = Read-Host -Prompt 'Please enter the application key: '
        Clear-Host
        $title    = ''
        $question = 'Is ' + $applicationKey + ' the correct application key?'
        $decision = $Host.UI.PromptForChoice($title, $question, $choices, 0)
        if ($decision -eq 0) {
            $loop = $False
        }
    } While ($loop)

    # Select Production or Development Server
    Clear-Host
    $loop = $true
    $serverDownload = 'https://sanimatic-dev.cloud.thingworx.com/Thingworx/FileRepositories/Downloads/microserver.zip?appKey=9f09c4f6-14f6-44b7-b90d-73a7e2f0e6ef'
    $server = 'sanimatic-dev.cloud.thingworx.com'
    DO {
        Clear-Host
        $title    = ''
        $question = 'Is this for the production server?'
        $decision = $Host.UI.PromptForChoice($title, $question, $choices, 0)
        if ($decision -eq 0) {
            $server = 'sanimatic-prod1.cloud.thingworx.com'
            $serverDownload = 'https://sanimatic-prod1.cloud.thingworx.com/Thingworx/FileRepositories/Downloads/microserver.zip?appKey=6234b184-ad06-470d-b648-55833f414343'
            $loop = $False
        } else {
            $loop = $False
        }
    } While ($loop)

    # Download Github Repository
    [String]$location = Split-Path -Parent $PSCommandPath
    DownloadGithubRepository -Location $location
    [String]$SaniTrendFolder = "$location\STC_Lite-main"

    # Change directory to respository folder
    Set-Location $SaniTrendFolder

    # Download edge microserver
    DownloadMicroServer -Location $pwd
    
    # File cleanup
    Remove-Item .gitignore
    Remove-Item LICENSE
    Remove-Item README.md
    Remove-Item requirements.txt
    Remove-Item sanitrend.service
    Remove-Item ssh.sh
    Remove-Item sudoers.sh
    Move-Item -Path $pwd\stc_lite.py -Destination $pwd\STC_Lite_Win
    Move-Item -Path $pwd\stc.py -Destination $pwd\STC_Lite_Win
    Move-Item -Path $pwd\SaniTrendConfig.json -Destination $pwd\STC_Lite_Win

    # SaniTrend Configuration File Setup
    (Get-Content $pwd\STC_Lite_Win\SaniTrendConfig.json) -replace 'PLC_IP_Address', $PLCIP | Set-Content $pwd\STC_Lite_Win\SaniTrendConfig.json
    (Get-Content $pwd\STC_Lite_Win\SaniTrendConfig.json) -replace 'ThingName', $SMINumber | Set-Content $pwd\STC_Lite_Win\SaniTrendConfig.json

    # Edge Microserver Configuration and Setup
    (Get-Content $pwd\microserver\etc\config.json) -replace 'ApplicationKey', $applicationKey | Set-Content $pwd\microserver\etc\config.json
    (Get-Content $pwd\microserver\etc\config.json) -replace 'ServerURL', $server | Set-Content $pwd\microserver\etc\config.json
    (Get-Content $pwd\microserver\etc\config.json) -replace 'ThingName', $SMINumber | Set-Content $pwd\microserver\etc\config.json
    $WSEMS_NAME = "Thingworx_WSEMS"
    [String]$configPath = "$pwd\microserver\etc\config.json"
    [String]$binPath = """$pwd\microserver\wsems.exe"" -service -cfg ""$configPath"""
    $service = Get-Service -Name $WSEMS_NAME -ErrorAction SilentlyContinue
    if($null -ne $service)
    {
        sc.exe delete + $WSEMS_NAME
    }

    $serviceParams = @{
        Name = $WSEMS_NAME
		BinaryPathName = $binPath
		DisplayName = $WSEMS_NAME
		StartupType = "auto"
		Description = "Thingworx Edge Microserver"
    }

    New-Service @serviceParams
    net start $WSEMS_NAME
    
    
    # SaniTrend Service Setup
    $sanitrendPath = "$PSScriptRoot\STC_Lite-main\STC_Lite_Win"
    $batPath = "$sanitrendPath\sanitrend.bat"
    $pythonPath = "$sanitrendPath\python.exe"
    $sanitrendFile = "$sanitrendPath\stc.py"
    New-Item $batPath
    Set-Content -Path $batPath -value "call $pythonPath $sanitrendFile"
    Set-Location -Path $sanitrendPath
    .\nssm.exe install SaniTrendCloud "$batPath"
    .\nssm.exe start SaniTrendCloud

    $msgBody = "SaniTrend Cloud installation complete."
    [System.Windows.MessageBox]::Show($msgBody,"SaniTrend Cloud Installer", 0,0)

} else {
    Exit
}

Exit