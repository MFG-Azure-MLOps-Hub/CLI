import json
import subprocess
import yaml
import argparse
import logging
import os
import uuid


# Function to run az cli
def cli_run(command):
    logging.info(command)
    run = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    # reading output and error
    stdout = run.stdout.decode("iso8859-1")  # Not 'utf-8'
    stderr = run.stderr.decode("iso8859-1")

    return stdout, stderr


def vg_exist(vg_name):
    command = f'az pipelines variable-group list -p {project_name} --org {org_url} --query "[].name" -o tsv'
    stdout, stderr = cli_run(command)
    if vg_name in stdout:
        return True
    else:
        return False


def pl_exit(pl_name):
    command = f'az pipelines list -p {project_name} --org {org_url} --repository {repo_name} --query "[].name" -o tsv'
    stdout, stderr = cli_run(command)
    if pl_name in stdout:
        return True
    else:
        return False


# Print cli_run results
def print_result(stdout, stderr):
    if stdout is not None and stdout != "":
        logging.debug(stdout)
    if stderr is not None and stderr != "":
        # raise SystemExit(stderr)
        logging.warning(stderr)


# Get the template file by using the source git url
def get_template(git_url):
    hub_db_file = 'hub_db.yml'
    with open(hub_db_file, 'r') as f:
        yml = yaml.safe_load(f)

    template = ""
    for project in yml['projects']:
        if project['git_url'] == git_url:
            template = project["template"]
    return template


# Intialize the logger
def init_logger():
    logging.basicConfig(
        filename='hub_install.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)


# python hub_install.py --org_url https://dev.azure.com/your_org
# --project_name mlopsproj
# --source_repo_url https://github.com/MFG-Azure-MLOps-Hub/MLOpsImgClass.git
parser = argparse.ArgumentParser("MLOps Hub Install")
parser.add_argument(
    "--org_url",
    type=str,
    required=True,
    help="Organization URL")
parser.add_argument(
    "--project_name",
    type=str,
    required=True,
    help="Your new project name")
parser.add_argument(
    "--source_repo_url",
    type=str,
    required=True,
    help="Source repo URL")

args = parser.parse_args()
org_url = args.org_url
project_name = args.project_name
source_repo_url = args.source_repo_url
# Use the project name for the repo name
repo_name = project_name
azure_resource_connection = 'azure-resource-connection'
init_logger()

# Read the project template yml file
template_file = get_template(source_repo_url)
if template_file == "":
    raise SystemExit("Template file not found.")

with open(template_file, 'r') as f:
    yml = yaml.safe_load(f)

# print("Login your Azure Devops Organization...")
# command = f"az devops login --org {org_url}"
# stdout, stderr = cli_run(command)
# print(stderr)

logging.info("Installation started.")
print("-" * 50)
logging.info(f"Step 1. Creating project '{project_name}' in {org_url} ...")
command = f"az devops project create --org {org_url} --name {project_name}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
logging.info(f"Created project:{project_name} in {org_url}.")

print("-" * 50)
logging.info(
    f"Step 2. Importing repo for '{project_name}' from {source_repo_url} ...")
command = f"az repos import create --git-url {source_repo_url} -p {project_name} --org {org_url} --repository {repo_name}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
logging.info(
    f"Imported repo:{source_repo_url} into {project_name} in {org_url}.")

print("-" * 50)
logging.info(f'Step 3. Creating variable groups for {project_name} ...')
for variable_group in yml['variable_groups']:
    vg_name = variable_group['variable_group']
    command = f"az pipelines variable-group create --name {variable_group['variable_group']} -p {project_name} --org {org_url} --authorize --variables "
    for key_value in variable_group['key_values']:
        for key, value in key_value.items():
            command = command + f"{key}={value} "
    stdout, stderr = cli_run(command)
    print_result(stdout, stderr)
    logging.info(
        f"Created variable Group:{vg_name} in {project_name} in {org_url}.")

# Create pipelines
print("-" * 50)
logging.info(f'Step 4. Creating pipelines for {project_name} ...')
for pipeline in yml['pipelines']:
    pl_name = pipeline['pipeline']
    yml_path = pipeline['file']
    command = f'az pipelines create -p {project_name} --org {org_url} --name {pl_name} --description {pl_name} --repository {repo_name} --repository-type tfsgit --branch master --skip-first-run --yml-path {yml_path}'
    stdout, stderr = cli_run(command)
    print_result(stdout, stderr)
    logging.info(f"Created pipeline:{pl_name} in {project_name} in {org_url}.")

# Create service connection 'azure_resource_connection'
print("-" * 50)
logging.info(f'Step 5. Creating service connections for {project_name} ...')
command = "az account show"
stdout, stderr = cli_run(command)
result = json.loads(stdout)
subcription_id = result["id"]
tenant_id = result["tenantId"]
subcription_name = result["name"]
environment = result["environmentName"]

sp_name = f"mfg-mlops-{uuid.uuid4()}"
command = f"az ad sp create-for-rbac --name http://{sp_name} --scopes /subscriptions/{subcription_id}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
result = json.loads(stdout)
app_id = result["appId"]
password = result["password"]

os.environ["AZURE_DEVOPS_EXT_AZURE_RM_SERVICE_PRINCIPAL_KEY"] = password
command = f'az devops service-endpoint azurerm create --azure-rm-service-principal-id {app_id} --azure-rm-subscription-id {subcription_id} --azure-rm-subscription-name "{subcription_name}" --azure-rm-tenant-id {tenant_id} --name {azure_resource_connection} -p {project_name} --org {org_url}'
stdout, stderr = cli_run(command)
print_result(stdout, stderr)

# Grant service connection access to all of the pipelines
command = f"az devops service-endpoint list --org {org_url} -p {project_name} --query \"[?name=='{azure_resource_connection}'].id\" -o tsv"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
se_id = stdout.strip()

command = f"az devops service-endpoint update --id {se_id} --enable-for-all true --org {org_url} -p {project_name}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
logging.info(
    f"Created service connection:{azure_resource_connection} in {project_name}.")

# Run IAC pipeline
print("-" * 50)
logging.info(f'Step 6. Running IAC Pipeline ...')
pl_name = "IAC"
command = f"az pipelines run --name {pl_name} --org {org_url} -p {project_name}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
result = json.loads(stdout)
pl_id = result["id"]
logging.info(f"Pipeline:{pl_id} {pl_name} started.")

import time
command = f"az pipelines build list --org {org_url} -p {project_name} --query [?id==`{pl_id}`].[id,result,status] -o tsv"
result = "N/A"
status = "N/A"
count = 0
s = ""
while 1:
    s = s + "."
    stdout, stderr = cli_run(command)
    if stdout is not None and stdout != "":
        pipeline = stdout.split()
        result = pipeline[1]
        status = pipeline[2]
    if stderr is not None and stderr != "":
        logging.warning(stderr)
    if status == "completed":
        # print(f"\r{s}")
        break
    else:
        print(f"Pipeline:{pl_id} {pl_name} status:{status}.")
        # print(f"\r{s}",end="")
    time.sleep(10)
    count = count + 1
    if count == 60:
        break


if result == "succeeded" and status == "completed":
    logging.info(f"Pipeline:{pl_id} {pl_name} status:{status}.")

# Create service connection 'aml-workspace-connection'
print("-" * 50)
logging.info(f'Step 7. Creating service connection "aml-workspace-connection" ...')
RESOURCE_GROUP = yml['variable_groups'][0]['key_values'][2]['RESOURCE_GROUP']
WORKSPACE_NAME = yml['variable_groups'][0]['key_values'][3]['WORKSPACE_NAME']
WORKSPACE_SVC_CONNECTION  = yml['variable_groups'][0]['key_values'][5]['WORKSPACE_SVC_CONNECTION']
LOCATION = yml['variable_groups'][0]['key_values'][1]['LOCATION']

def process_json():
    file_in = open("./configuration.json", "r")
    file_out = open("./configuration.temp.json", "w")
    # load data to json_data variable
    json_data = json.load(file_in)
    # print (json_data)
    # print ("after update  --->")
    # print (type(json_data))
    # Change configuration data
    json_data["authorization"]["parameters"]["tenantid"] = tenant_id
    json_data["authorization"]["parameters"]["scope"] = f"/subscriptions/{subcription_id}/resourcegroups/{RESOURCE_GROUP}/providers/Microsoft.MachineLearningServices/workspaces/{WORKSPACE_NAME}"
    json_data["data"]["environment"] = environment
    json_data["data"]["subscriptionId"] = subcription_id
    json_data["data"]["subscriptionName"] = subcription_name
    json_data["data"]["resourceGroupName"] = RESOURCE_GROUP
    json_data["data"]["mlWorkspaceName"] = WORKSPACE_NAME
    json_data["data"]["mlWorkspaceLocation"] = LOCATION
    json_data["name"] = WORKSPACE_SVC_CONNECTION
    # print (json_data)
    # write to new file
    file_out.write(json.dumps(json_data))
    file_in.close()
    file_out.close()

process_json()
command = f'az devops service-endpoint create --service-endpoint-configuration configuration.temp.json -p {project_name} --org {org_url}'
stdout, stderr = cli_run(command)
os.remove("./configuration.temp.json")
print_result(stdout, stderr)

# Grant service connection access to all of the pipelines
command = f"az devops service-endpoint list --org {org_url} -p {project_name} --query \"[?name=='{WORKSPACE_SVC_CONNECTION}'].id\" -o tsv"
count = 0
se_id = None
while 1:
    stdout, stderr = cli_run(command)
    print_result(stdout, stderr)
    se_id = stdout.strip()
    if se_id != None and se_id !="":
        break
    time.sleep(5)
    count = count + 1
    if count == 60:
        break

command = f"az devops service-endpoint update --id {se_id} --enable-for-all true --org {org_url} -p {project_name}"
stdout, stderr = cli_run(command)
print_result(stdout, stderr)
logging.info(
    f"Created service connection:{WORKSPACE_SVC_CONNECTION} in {project_name}.")

logging.info('Installation finished.')
