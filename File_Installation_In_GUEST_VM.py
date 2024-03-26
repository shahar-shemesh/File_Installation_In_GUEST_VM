import re
import paramiko
import os
import time
import datetime
import stat
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import tkinter.messagebox as messagebox


# ----------------------------------------------------------------#

# establish SSH connection to retrieve creation date file

def get_creation_date(path):
    temp_ssh = create_ssh_connection()  # create SSH connection
    try:
        stdin, stdout, stderr = temp_ssh.exec_command(fr"powershell (Get-Item '{path}').CreationTime")  # execute PowerShell command to get creation time
        output = stdout.read().decode().strip()  # read output of command
        temp_ssh.close()

        try:
            # parse creation date and return timestamp
            output_datatime = datetime.strptime(output, "%A, %B %d, %Y %I:%M:%S %p")  # convert output to datetime object
            return int(output_datatime.timestamp())  # return timestamp

        except ValueError as e:  # handle value error
            return 0  # return 0 if unable to parse

    except paramiko.SSHException as e:  # handle SSH exception
        print("SSH error: ", e)
        return 0  # return 0 in case of error


# ----------------------------------------------------------------#

# Create powershell script to execute a remote file silently
def create_ps1_script(local_folder, remote_path):
    script_content = f'Start-Process "{remote_path}" -ArgumentList "/silent", "/S", "/quiet", "/qn" -Wait -PassThru'  # create PowerShell script content
    script_path = os.path.join(local_folder, "install.ps1")  # set script path

    try:
        with open(script_path, 'w') as f:  # open script file for writing
            f.write(script_content)  # write script content to file
    except IOError as e:  # handle IO error
        print("Error writing script file: ", e)

    return script_path


# ----------------------------------------------------------------#


# list relevant files in a directory
def list_files(sftp, path, remote_folder):
    last_hour = int(time.time()) - 3600  # calculate timestamp for one hour ago
    folders = []
    relevant_files = []

    def rec_files(sftp, path):  # recursive function to list files
        for item in sftp.listdir_attr(path):  # iterate over items in directory
            if not (item.filename).startswith("$"):  # check if filename does not start with '$'

                item_path = fr"{path}\{item.filename}"  # get the full path of the item

                creation_date = get_creation_date(item_path)  # get creation date of item

                is_folder = stat.S_ISDIR(item.st_mode)  # check if item is a folder

                if creation_date > 0:  # if creation date is valid
                    if not is_folder and (creation_date > last_hour):  # if item is a file and created within last hour
                        relevant_files.append(item_path)  # add file to relevant files
                    elif is_folder and (item.st_mtime > last_hour):  # if item is a folder and modified within last hour
                        folders.extend(rec_files(sftp, item_path))  # recursively list files in folder
        return relevant_files  # return relevant files

    try:
        files = rec_files(sftp, path)  # call recursive function to list files
        files = [path for path in files if remote_folder not in path]
        return files  # return relevant files
    except IOError as e:  # handle IO error
        print("Error listing files:", e)
        return []  # return empty list in case of error


# ----------------------------------------------------------------#


# Install and execute files
def install_exec_files(local_folder, remote_folder, progress_var, status_label):
    # Create the remote folder if it doesn't exist
    ssh_new_folder = create_ssh_connection()
    try:
        ssh_new_folder.exec_command(fr"mkdir {remote_folder}")
    except paramiko.SSHException as e:
        print("Error creating remote folder:", e)
    ssh_new_folder.close()

    # Iterate over files in the local folder
    file_count = len(os.listdir(local_folder))  # count files in local folder
    progress_unit = 100 / file_count  # calculate progress unit

    for index, filename in enumerate(os.listdir(local_folder)): # iterate over files in local folder
        file_ssh = create_ssh_connection()
        sftp = file_ssh.open_sftp()

        local_path = fr"{local_folder}\{filename}"  # set local file path
        remote_path = fr"{remote_folder}\{filename}"  # set remote file path

        # Copy the file to the guest VM
        try:
            sftp.put(local_path, remote_path)
            sftp.stat(remote_path)
        except IOError as e:
            print("Error copying file: ", e)
            continue

        # Install the file if it's executable
        script_local_path = create_ps1_script(local_folder, remote_path)
        script_remote_path = fr"{remote_folder}\install.ps1"
        try:
            sftp.put(script_local_path, script_remote_path)  # copy script to remote VM
            sftp.stat(script_remote_path)  # get script status
        except IOError as e:  # handle IO error
            print("Error copying script file:", e)
            continue  # continue to next file

        # Execute the script on remote machine
        file_ssh.exec_command(f'powershell -ExecutionPolicy Bypass -File {script_remote_path}')  # execute script on remote machine
        time.sleep(10) # wait for execution to complete
        os.remove(script_local_path)  # remove local script file

        # Retrieve relevant files from the remote machine

        root_path = re.sub('[^a-zA-Z]+', '', drive_path_entry.get()) + ":"  # set root path

        attempts = 0
        while attempts < 3:
            remote_paths = list_files(sftp, root_path, remote_folder)  # list relevant files on remote machine
            if not len(remote_paths):
                time.sleep(60)  # wait for execution to complete
                attempts += 1
            else:
                break

        file_basename = os.path.basename(filename[:-4])  # get basename without type of the file

        if attempts >= 3:
            messagebox.showerror(f"{file_basename} Installation Failed", f"The installation {file_basename} has failed. Please check the installation file.")
            continue


        files_local_path = os.path.join(local_folder, file_basename)  # set local path for files

        try:
            os.mkdir(files_local_path)  # create directory for files
        except FileExistsError:  # handle file exists error
            pass  # do nothing if directory already exists


        for remote_path_file in remote_paths:  # iterate over remote file paths
            file_name = os.path.basename(remote_path_file)  # get file name
            local_path_file = os.path.join(files_local_path, file_name)  # set local file path

            try:
                sftp.get(remote_path_file, local_path_file)  # retrieve file from remote machine
                sftp.remove(remote_path_file)  # remove file from remote machine after retrieval
            except IOError as e:  # handle IO error
                print("Error retrieving or removing file: ", e)

        sftp.close()
        file_ssh.close()

        # Update progress bar and status label
        progress_var.set(int((index + 1) * progress_unit))
        status_label.config(text=f"Processing: {index + 1}/{file_count}")
        status_label.update_idletasks()


# ----------------------------------------------------------------#

# create SSH connection to the guest
def create_ssh_connection():
    hostname = hostname_entry.get()  # get hostname from GUI entry
    port = int(port_entry.get())  # get port from GUI entry
    username = username_entry.get()  # get username from GUI entry
    password = password_entry.get()  # get password from GUI entry
    ssh = paramiko.SSHClient()  # create SSH client object
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # set missing host key policy
    try:
        ssh.connect(hostname, port, username, password)  # establish SSH connection
    except paramiko.SSHException as e:  # handle SSH exception
        print("SSH Connection error: ", e)
    return ssh  # return SSH connection


# ----------------------------------------------------------------#


# Create GUI
def browse_button():
    global folder_path_entry
    filename = filedialog.askdirectory()  # open file dialog to select folder
    folder_path_entry.delete(0, tk.END)  # clear folder path entry
    folder_path_entry.insert(0, filename)  # insert selected folder path into entry


def start_execution():
    local_folder = folder_path.get()  # get local folder path from GUI entry
    root_path = re.sub('[^a-zA-Z]+', '', drive_path_entry.get()) + ":"
    #remote_folder = r'C:\Users\Administrator\Desktop\installFilesFromHost'  # set remote folder path
    remote_folder = fr'{root_path}\installFilesFromHost'  # set remote folder path


    if local_folder:  # if local folder path is not empty
        progress_var.set(0)  # set progress bar to 0

        status_label.config(text="Process started...")  # update status label

        install_exec_files(local_folder, remote_folder, progress_var, status_label)  # start installation and execution process

        status_label.config(text="Process completed.")  # update status label

    else:  # if local folder path is empty
        status_label.config(text="Please select a folder.")  # update status label


root = tk.Tk()  # create Tkinter root window
root.title("File Installation In GUEST VM")  # set window title

folder_path = tk.StringVar()  # store folder path

label = tk.Label(root, text="Select the folder containing files to install:")
label.pack()

folder_path_entry = tk.Entry(root, textvariable=folder_path, width=50)  # create entry for folder path
folder_path_entry.pack()  # add entry to window

browse_button = tk.Button(root, text="Browse", command=browse_button)  # create browse button
browse_button.pack()  # add browse button to window

drive_path_label = tk.Label(root, text='Guest Drive Path: ("C", "D", "G" etc.)')
drive_path_label.pack()

drive_path_entry = tk.Entry(root, width=3)
drive_path_entry.pack()

###### GUI elements for SSH connection  ########

hostname_label = tk.Label(root, text="Hostname:")  # label for hostname
hostname_label.pack()  # add label to window

hostname_entry = tk.Entry(root)  # entry for hostname
hostname_entry.pack()  # add entry to window

port_label = tk.Label(root, text="Port:")  # label for port
port_label.pack()  # add label to window

port_entry = tk.Entry(root)  # create entry for port
port_entry.pack()  # add entry to window

username_label = tk.Label(root, text="Username:")  # create label for username
username_label.pack()  # add label to window

username_entry = tk.Entry(root)  # create entry for username
username_entry.pack()  # add entry to window

password_label = tk.Label(root, text="Password:")  # create label for password
password_label.pack()  # add label to window

password_entry = tk.Entry(root, show="*")  # entry for password (password is hidden)
password_entry.pack()  # add entry to window

start_button = tk.Button(root, text="Start Execution", command=start_execution)  # create start execution button
start_button.pack()  # add start button to window

progress_var = tk.DoubleVar()  # variable for progress bar
progress_bar = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate', variable=progress_var)  # create progress bar
progress_bar.pack()  # add progress bar to window

status_label = tk.Label(root, text="")  # create status label
status_label.pack()  # add status label to window

root.mainloop()  # start GUI main loop