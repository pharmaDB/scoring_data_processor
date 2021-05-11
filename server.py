"""
This file will run a simple server.
Port 80 of firewall needs to be made available to all users.
Run with `nohup python3 server.py &` with no quotes.
"""

import os
from http.server import HTTPServer, CGIHTTPRequestHandler

# Set host folder name here:
folder_name = "./resources/hosted_folder/"

# Make folder if non-existant
folder_name = os.path.abspath(folder_name)
if not os.path.exists(os.path.dirname(folder_name)):
    os.makedirs(os.path.dirname(folder_name))

# Make sure the server is created at current directory
os.chdir(folder_name)

# Create server object listening the port 80
server_object = HTTPServer(
    server_address=("", 80), RequestHandlerClass=CGIHTTPRequestHandler
)

# Start the web server
server_object.serve_forever()
