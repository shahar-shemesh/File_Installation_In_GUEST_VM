# File Installation In GUEST VM

This project aims to automate the process of installing and executing files on a guest virtual machine (VM) via SSH connection. The script establishes an SSH connection to the guest VM and allows the user to select a local folder containing files to be installed and executed on the VM. It copies the files to the VM, installs them if executable, executes PowerShell scripts silently, and retrieves relevant files from the VM.

<p align="center">
    <img src="https://ik.imagekit.io/shahar/file-installation.jpg"/>
</p>



## Features
- Establish SSH connection to the guest VM.
- Select a local folder containing files to install.
- Copy files to the remote VM.
- Install executable files.
- Execute PowerShell scripts silently.
- Retrieve relevant files from the VM.
- Display progress using a GUI with a progress bar and status updates.


## Requirements
- Python 3.x
- Paramiko library
- Tkinter library (usually included with Python)
- A guest VM accessible via SSH with appropriate credentials
- Necessary permissions to execute PowerShell scripts on the guest VM


## Usage
1. Clone or download the script.

2. Install the required libraries if not already installed:
```bash
pip install paramiko
```

3. Run the script:
```bash
python File_Installation_In_GUEST_VM.py
```

4. Fill in the required information in the GUI:
- Select the local folder containing files to install.
- Specify the drive path on the guest VM.
- Hostname, Port, Username, and Password for SSH connection.


5. Click on the "Start Execution" button to initiate the installation process.

6. Monitor the progress through the progress bar and status updates.

7. Upon completion, relevant files will be retrieved from the guest VM.

