#!/bin/sh
# Get SMI Number
clear
shouldloop=true;
while $shouldloop; do
    echo -n "Please enter the SMI Number: "
    read SMINumber
    clear
    echo -n "Is $SMINumber the correct SMI Number (y/n)?: "
    read answer
    if [ "$answer" != "${answer#[Yy]}" ]; then
        shouldloop=false;
    fi
done

# Get PLC IP Address
clear
shouldloop=true;
while $shouldloop; do
    echo -n "Please enter the PLC IP Address: "
    read PLCIP
    clear
    echo -n "Is $PLCIP the correct IP Address (y/n)?: "
    read answer
    if [ "$answer" != "${answer#[Yy]}" ]; then
        shouldloop=false;
    fi
done

# Get Application Key
clear
shouldloop=true;
while $shouldloop; do
    echo -n "Please enter application key: "
    read applicationKey
    clear
    echo -n "Is $applicationKey the correct application key (y/n)?: "
    read answer
    if [ "$answer" != "${answer#[Yy]}" ]; then
        shouldloop=false;
    fi
done

# Select Production or Development Server
clear
shouldloop=true;
serverDownload="https://sanimatic-dev.cloud.thingworx.com/Thingworx/FileRepositories/Downloads/linuxmicroserver.zip?appKey=9f09c4f6-14f6-44b7-b90d-73a7e2f0e6ef"
server="sanimatic-dev.cloud.thingworx.com"
while $shouldloop; do
    echo -n "Is this for the production server (y/n)?: "
    read answer
    if [ "$answer" != "${answer#[Yy]}" ]; then
        server="sanimatic-prod1.cloud.thingworx.com"
        serverDownload="https://sanimatic-prod1.cloud.thingworx.com/Thingworx/FileRepositories/Downloads/linuxmicroserver.zip?appKey=6234b184-ad06-470d-b648-55833f414343"
        shouldloop=false;
    else
        shouldloop=false;
    fi
done

# Update the system
clear
echo "Updating the system..."
sudo apt update && sudo apt upgrade -y

# Install Prerequisite Programs
echo "\n\n\nInstalling Prerequisite programs..."
sudo apt install -y git curl wget zip unzip python3 python3-pip sqlite3

# Clone SaniTrend Cloud github repository
echo "\n\n\nDownloading SaniTrend Cloud Repository..."
git clone https://github.com/msienkow/STC_Lite.git
cd STC_Lite

# SaniTrend Config File
echo "\n\n\nCreating SaniTrend Cloud configuration file..."
sed -i s"|PLC_IP_Address|$PLCIP|g" SaniTrendConfig.json
sed -i s"|ThingName|$SMINumber|g" SaniTrendConfig.json

# Install python 3 requirements
echo "\n\n\nInstalling python3 required libraries..."
sudo pip3 install -r requirements.txt

# Enable any user to reboot computer
echo "\n\n\nApplying settings to allow any user to reboot the system..."
chmod +x sudoers.sh
sudo ./sudoers.sh

# Change SSH settings

echo "\n\n\nModifying SSH settings..."
chmod +x ssh.sh
sudo ./ssh.sh
echo "Restarting ssh daemon..."
sudo systemctl restart ssh

# Dowload/Configure Thingworx Edge Microserver
echo "\n\n\nDownloading Thingworx Edge Microserver..."
wget -O microserver.zip $serverDownload
unzip microserver.zip
rm microserver.zip

# Install Thingworx Edge Microserver
echo "\n\n\nInstalling Thingworx Edge Microserver..."
cd microserver
chmod +x wsems
echo "Encrypting Application Key..."
key=`./wsems -encrypt $applicationKey | sed -n '3{p;q}'`
sed -i s"|ServerURL|$server|g" etc/config.json
sed -i s"|ApplicationKey|$key|g" etc/config.json
sed -i s"|ThingName|$SMINumber|g" etc/config.json
cd install_services
chmod +x install
sudo ./install
cd ../..

# Setup Thinworx Edge Microserver for automatic Systemd Service
echo "\n\n\nInstalling SaniTrend Cloud Systemd service..."
sudo cp sanitrend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sanitrend.service
sudo systemctl start sanitrend.service

# File cleanup
rm .gitignore
rm LICENSE
rm README.md
rm requirements.txt
rm sanitrend.service
rm ssh.sh
rm sudoers.sh
rm SaniTrendCloud.ps1
rm -rf STC_Lite_Win

# End of Script
echo "\n\n\n***********************************************"
echo "**** SaniTrend Lite Installation Complete *****"
echo "***********************************************\n\n\n"