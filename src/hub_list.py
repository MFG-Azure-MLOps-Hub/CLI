import yaml

hub_db_file = 'hub_db.yml'
with open(hub_db_file, 'r') as f:
    yml = yaml.safe_load(f)

print("-" * 50)
print("Templates in MFG Azure MLOps Hub")
print("-" * 50)
i = 1
for project in yml['projects']:
    print(f"{i}.{project['project']}")
    print(f"  {project['description']}")
    print(f"  {project['git_url']}")
    print("\n")
    i = i+1
