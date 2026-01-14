import os
import json

class UserFile:
    def __init__(self,user):
        self.user = user
        self.file_path = f'./user_files/{user}'
        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)
        self.user_project = os.listdir(self.file_path)
        self.project_content = {}
    
    def init_project(self,project_name):
        i = 1
        new_project_name = project_name
        while new_project_name in self.user_project:
            new_project_name = f"{project_name}_{i}"
            i += 1
        self.user_project.append(new_project_name)
        self.project_content[new_project_name] = {}
        os.makedirs(os.path.join(self.file_path,new_project_name))
        return new_project_name
    
    def load_content(self,project_name):
        if project_name not in self.user_project:
            raise FileNotFoundError(f"项目 {project_name} 不存在")
        with open(os.path.join(self.file_path,project_name, 'project.json'), 'r', encoding='utf-8') as file:
            self.project_content[project_name] = json.load(file)
        return self.project_content[project_name]
    
    def save_content(self,project_name,content):
        if project_name not in self.user_project:
            os.makedirs(os.path.join(self.file_path,project_name))
            self.user_project.append(project_name)
        self.project_content[project_name] = content
        with open(os.path.join(self.file_path,project_name, 'project.json'), 'w', encoding='utf-8') as file:
            json.dump(content, file, ensure_ascii=False, indent=4)