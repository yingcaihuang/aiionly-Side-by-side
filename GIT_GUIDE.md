# Git 提交指南

## 首次提交到 GitHub

### 1. 检查当前状态

```bash
git status
```

### 2. 添加所有文件（排除 .gitignore 中的文件）

```bash
git add .
```

### 3. 查看将要提交的文件

```bash
git status
```

**确保以下文件被忽略（不应出现在列表中）：**
- `config.yaml` (包含 API 密钥)
- `*.log` 文件
- `__pycache__/` 目录
- `.venv/` 或 `venv/` 目录

### 4. 提交更改

```bash
git commit -m "feat: 初始提交 - AI 模型对比中心"
```

### 5. 在 GitHub 上创建仓库

1. 访问 https://github.com/new
2. 填写仓库名称：`model-comparison-system`
3. 选择 Public 或 Private
4. **不要**初始化 README、.gitignore 或 LICENSE（我们已经有了）
5. 点击 "Create repository"

### 6. 添加远程仓库

```bash
git remote add origin https://github.com/your-username/model-comparison-system.git
```

**替换 `your-username` 为您的 GitHub 用户名**

### 7. 推送到 GitHub

```bash
# 推送主分支
git push -u origin main

# 如果您的默认分支是 master
git push -u origin master
```

### 8. 验证

访问您的 GitHub 仓库页面，确认所有文件都已上传。

## 后续更新

### 添加更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
git push
```

### 常用提交类型

- `feat: 新功能`
- `fix: 修复bug`
- `docs: 文档更新`
- `style: 代码格式`
- `refactor: 重构`
- `test: 测试`
- `chore: 构建/工具`

## 安全检查清单

在推送前，确保：

- [ ] `config.yaml` 在 .gitignore 中
- [ ] 没有硬编码的 API 密钥
- [ ] 日志文件被忽略
- [ ] 虚拟环境目录被忽略
- [ ] `config.yaml.example` 不包含真实密钥

## 查看忽略的文件

```bash
git status --ignored
```

## 如果不小心提交了敏感信息

### 从最后一次提交中移除

```bash
git rm --cached config.yaml
git commit --amend -m "fix: 移除敏感配置文件"
git push --force
```

### 从历史记录中完全移除

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.yaml" \
  --prune-empty --tag-name-filter cat -- --all

git push --force --all
```

**注意：** 如果已经推送了包含密钥的提交，应该：
1. 立即撤销该密钥
2. 生成新的 API 密钥
3. 更新本地 `config.yaml`

## 有用的 Git 命令

```bash
# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v

# 拉取最新更改
git pull

# 创建新分支
git checkout -b feature/new-feature

# 切换分支
git checkout main

# 合并分支
git merge feature/new-feature

# 删除本地分支
git branch -d feature/new-feature
```

## 需要帮助？

- Git 文档：https://git-scm.com/doc
- GitHub 指南：https://guides.github.com/
