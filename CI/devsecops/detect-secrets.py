import json
import subprocess
import requests
import os
import sys
from tabulate import tabulate

#gitlab variable
gitlab_url = os.environ.get('CI_SERVER_URL')
project_dir = os.environ.get('CI_PROJECT_PATH')
current_branch = os.environ.get('CI_COMMIT_BRANCH')
fwork_url = os.environ.get('FWORK_URL')
EXCLUDE_FOLDERS = 'EXCLUDE_FOLDERS'
exclude_folders= os.environ.get('EXCLUDE_FOLDERS')
EXCLUDE_SECRETS = 'EXCLUDE_SECRETS'
exclude_secrets = os.environ.get('EXCLUDE_SECRETS')


print("////////////////////////////////  Command out put  //////////////////////////////////////////////////" + "\n")
# Send request to Fwork
def send_request(type,filename,line_number,gitlab_url,project_dir,current_branch):
    url = f'{fwork_url}'
    headers = {'Content-Type': 'application/json'}
    data = {
        "receiver": "fwork-webhook",
        "status": "firing",
        "alerts": [{
                "status": "firing",
                "labels": {
                    "alertname": "SECRET FOUND",
                    "env": f"{current_branch}",
                    "location": f"{gitlab_url}/{project_dir}/-/blob/{current_branch}/{filename}#L{line_number}",
                    "job": "secrets scan",
                    "type": f"{type}",
                    "project": f"{project_dir}",
                    "pic": "",
                    "severity": "critical"
                }
            }
        ],
        "commonLabels": {
            "alertname": "SECRET FOUND",
            "env": f"{current_branch}",
            "location": f"{gitlab_url}",
            "job": "secrets scan",
            "project": f"{project_dir}",
            "severity": "critical"
        },
        "commonAnnotations": {
            "description": f"{current_branch} - Secret found at {project_dir}",
            "summary": "Secret found"
        }
    }

    # Send HTTPS request
    response = requests.post(url, headers=headers, json=data)

    # Print response
    print("Send request to Fwork",response.text)

command = ["detect-secrets", "-C", f"/builds/{project_dir}/", "scan", "--all-files","--exclude-files",".*\.yaml$","--exclude-files",".*\.yml$","--exclude-files",".*\.dccache$"]
# Read lines from environment
if EXCLUDE_FOLDERS in os.environ:
    folders = exclude_folders.split(';')
    print("exclude folders: ",folders)
    for folder in folders:
        command.extend(["--exclude-files", folder])

if EXCLUDE_SECRETS in os.environ:
    secrets = exclude_secrets.split('|')
    print("exclude secrets: ",secrets)
    with open("/app/wordlist.txt", 'w') as file:
        for secret in secrets:
            file.write(secret + "\n")
    command.extend(["--word-list", "/app/wordlist.txt"])

#scan for secrets
print("command: " + ' '.join(command))

result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#print table
def print_table(table_data):
    # Define the table headers
    headers = ["Type", "Filename", "Line Number"]

    # Draw the table
    table = tabulate(table_data, headers, tablefmt="grid")

    # Print the table
    print(table)

if result.returncode == 0:
    output = result.stdout.decode()
    try:
        json_output = json.loads(output)
        json_data = json.dumps(json_output, indent=2)
        print("////////////////////////////////  Command out put  //////////////////////////////////////////////////" + "\n")
        print(json_output)
        print("////////////////////////////////  Send secrets found to Fwork   /////////////////////////////////////" + "\n")
        results = json_output['results']
        values = results.values()
        table_data = []
        for value in values:
            type = value[0]['type']
            filename = value[0]['filename']
            len_project_dir = len(project_dir)
            filename = filename[(len_project_dir + 9):] #filename[(len_project_dir + 9)] = /builds/{project_dir}/
            line_number = value[0]['line_number']
            #print result
            # Create a new row using variables and append it to table_data
            row = [type, filename, line_number]
            table_data.append(row)
            #send request to Fwork
            send_request(type,filename,line_number,gitlab_url,project_dir,current_branch)
        print("////////////////////////////////  List of secrets found   ////////////////////////////////////////////" + "\n")
        print_table(table_data)
        if len(values) != 0:
            print("\nSecrets found. Make job failed.")
            sys.exit(1)
    except ValueError as e:
        print("Error parsing output as JSON:", e)
else:
    print(result.stderr.decode())
