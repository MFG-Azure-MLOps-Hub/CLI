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
tenant_id = result["homeTenantId"]
subcription_name = ["name"]
# print(subcription_id)
# print(tenant_id)

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

logging.info('Installation finished.')
