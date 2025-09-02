# PowerShell命令删除虚拟环境
Remove-Item -Path .venv -Recurse -Force

# 创建新的虚拟环境
python -m venv .venv

# 激活虚拟环境
& .\.venv\Scripts\Activate.ps1

# 安装项目
pip install -e .
