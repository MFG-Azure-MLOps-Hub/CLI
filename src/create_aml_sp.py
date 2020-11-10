import json
import subprocess
import yaml
import argparse
import logging
import os
import uuid

# Function to run az cli


def cli_run(command):
    print(command)
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


def print_result(stdout, stderr):
    if stdout is not None and stdout != "":
        print(stdout)
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


def init_logger():
    logging.basicConfig(
        filename='hub_install.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

#TODO: Edit AML Service Principle Config File


# python hub_install.py --org_url https://dev.azure.com/ganwa
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
azure_resource_connection = 'azure-resource-connection-aml2'
init_logger()

# Read the project template yml file
template_file = get_template(source_repo_url)
if template_file == "":
    raise SystemExit("Template file not found.")

with open(template_file, 'r') as f:
    yml = yaml.safe_load(f)

RESOURCE_GROUP = yml['variable_groups'][0]['key_values'][2]['RESOURCE_GROUP']
WORKSPACE_NAME = yml['variable_groups'][0]['key_values'][3]['WORKSPACE_NAME']
WORKSPACE_SVC_CONNECTION  = yml['variable_groups'][0]['key_values'][5]['WORKSPACE_SVC_CONNECTION']
LOCATION = yml['variable_groups'][0]['key_values'][1]['LOCATION']
# Create service connection 'azure_resource_connection'
print("-" * 50)
print(RESOURCE_GROUP)
logging.info(f'Step 5. Creating service connections for {project_name} ...')
command = "az account show"
stdout, stderr = cli_run(command)
result = json.loads(stdout)
subcription_id = result["id"]
print('test:')
print(subcription_id)
tenant_id = result["tenantId"]
subcription_name = result["name"]
environment = result["environmentName"]

# print(subcription_id)
# print(tenant_id)
def process_json():
    file_in = open("./configuration.json", "r")
    file_out = open("./configuration.temp.json", "w")
    # load数据到变量json_data
    json_data = json.load(file_in)
    print (json_data)
    print ("after update  --->")
    print (type(json_data))
    # 修改json中的数据
    json_data["authorization"]["parameters"]["tenantid"] = tenant_id
    json_data["authorization"]["parameters"]["scope"] = "/subscriptions/0fcc2c21-cb77-435a-bf1d-341d1e767f00/resourcegroups/mfgmlops-RG/providers/Microsoft.MachineLearningServices/workspaces/mfgmlops-AML-WS"
    json_data["data"]["environment"] = environment
    json_data["data"]["subscriptionId"] = subcription_id
    json_data["data"]["subscriptionName"] = subcription_name
    json_data["data"]["resourceGroupName"] = RESOURCE_GROUP
    json_data["data"]["mlWorkspaceName"] = WORKSPACE_NAME
    json_data["data"]["mlWorkspaceLocation"] = LOCATION
    json_data["name"] = WORKSPACE_SVC_CONNECTION
    print (json_data)
    # 将修改后的数据写回文件
    file_out.write(json.dumps(json_data))
    file_in.close()
    file_out.close()

process_json()
command = f'az devops service-endpoint create --service-endpoint-configuration configuration.temp.json -p mlopsproj --org https://dev.azure.com/DevOpsTestYH'
stdout, stderr = cli_run(command)
os.remove("./configuration.temp.json")
print_result(stdout, stderr)




# # Grant service connection access to all of the pipelines
# command = f"az devops service-endpoint list --org {org_url} -p {project_name} --query \"[?name=='{azure_resource_connection}'].id\" -o tsv"
# stdout, stderr = cli_run(command)
# print_result(stdout, stderr)
# se_id = stdout.strip()

# command = f"az devops service-endpoint update --id {se_id} --enable-for-all true --org {org_url} -p {project_name}"
# stdout, stderr = cli_run(command)
# print_result(stdout, stderr)
# logging.info(
#     f"Created service connection:{azure_resource_connection} in {project_name}.")

# logging.info('Installation finished.')

# subcription_name = ["name"]
# # print(subcription_id)
# # print(tenant_id)

