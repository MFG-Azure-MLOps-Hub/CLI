# The CLI of Azure-MLOps Hub for Manufacturing

The content of CLI
1. **List Templates** - list the MLOps templates
2. **Deploy Template** - generate MlOps project in [Azure DevOps](http://dev.azure.com), including repo and CI/CD pipeline

## Install
1. [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. Add the Azure DevOps Extension
```
az extension add --name azure-devops
```
3. Clone the repo of The CLI of Azure-MLOps Hub for Manufacturing
``` shell
git clone https://github.com/MFG-Azure-MLOps-Hub/CLI.git
```

## List templates

```
python hub_list.py
```

## Deploy Template

```
python hub_install.py  --project_name {project_name} --org_url {org_url} --source_repo_url {repo_name}
```
example, to deploy **MLOpsImgClass** as a template

```
python hub_install.py  --org_url https://dev.azure.com/your_org --project_name mlopsproj --source_repo_url https://github.com/MFG-Azure-MLOps-Hub/MLOpsImgClass.git
```
