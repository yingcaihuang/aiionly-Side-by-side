# AI 模型对比中心 🤖

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Gradio](https://img.shields.io/badge/Gradio-4.0+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

一个现代化的 Web 应用，用于实时并发对比多个 AI 模型的响应结果。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [配置说明](#️-配置说明) • [使用指南](#-使用指南)

</div>

## 📸 应用截图

<div align="center">

![应用界面](screencapture-127-0-0-1-7860-2026-03-06-08_49_07.png)

*AI 模型对比中心 - 实时并发对比多个 AI 模型的响应*

</div>

---

## ✨ 功能特性

- **🚀 并发请求** - 同时向多个 AI 模型发送请求，最小化总响应时间
- **📊 实时对比** - 流式显示每个模型的响应，无需等待所有模型完成
- **🎨 现代化 UI** - 精美的渐变设计、卡片布局和流畅动画
- **📝 Markdown 渲染** - 完整支持 Markdown 格式，包括代码块、表格、列表等
- **⚡ 快捷操作** - 支持 Ctrl+Enter / ⌘+Enter 快速提交
- **📋 一键复制** - 轻松复制任何模型的响应内容
- **🛡️ 错误处理** - 智能错误解析和友好的故障排除提示
- **⚙️ 灵活配置** - 通过 YAML 文件轻松配置 API 和模型设置

## 🎯 支持的模型

通过 MAAS API 支持以下 AI 模型：

- **glm-4.6v-flash** - GLM-4 Flash 模型，快速高效
- **gpt-oss-120b** - GPT OSS 120B 大型开源模型
- **grok-4** - Grok-4 高级推理模型
- **gemini-2.5-flash** - Google Gemini 2.5 Flash 多模态模型

## 🚀 快速开始

### 前置要求

- Python 3.8 或更高版本
- MAAS API 密钥（从 [https://maas.aiionly.com](https://maas.aiionly.com) 获取）
- 稳定的网络连接

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/your-username/model-comparison-system.git
cd model-comparison-system
```

2. **创建虚拟环境**

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Linux/Mac)
source venv/bin/activate

# 激活虚拟环境 (Windows)
venv\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

### 配置

1. **创建配置文件**

```bash
cp config.yaml.example config.yaml
```

2. **编辑配置文件**

打开 `config.yaml` 并更新您的 API 密钥：

```yaml
api:
  api_key: "your-actual-api-key-here"  # 替换为您的 MAAS API 密钥
```

### 运行应用

```bash
python -m model_comparison_system.main
```

应用将在 `http://localhost:7860` 启动。在浏览器中打开此地址即可使用。

## ⚙️ 配置说明

### API 设置

| 设置 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `base_url` | MAAS API 端点 URL | `https://api.aiionly.com` | 是 |
| `api_key` | 您的 MAAS API 密钥 | - | 是 |
| `timeout` | 请求超时时间（秒） | `30` | 否 |
| `max_retries` | 最大重试次数 | `3` | 否 |

### 模型设置

| 设置 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `supported_models` | 可用的模型 ID 列表 | 全部 4 个模型 | 是 |
| `default_models` | 默认使用的模型 | 全部支持的模型 | 是 |
| `max_parallel_calls` | 最大并发请求数 | `4` | 否 |

## 📖 使用指南

### 基本使用

1. 在输入框中输入您的提示词
2. 按 `Ctrl+Enter` (Windows/Linux) 或 `⌘+Enter` (Mac)，或点击"开始对比"按钮
3. 实时查看每个模型的响应
4. 点击"复制回答"按钮复制任何模型的响应

### 使用场景示例

**基础对比**
```
提示词：用简单的语言解释量子计算
```

**创意写作**
```
提示词：写一个关于机器人学习绘画的短篇故事
```

**技术问题**
```
提示词：如何在 Python 中实现二叉搜索树？
```

## 🛠️ 开发

### 项目结构

```
model_comparison_system/
├── model_comparison_system/     # 主包
│   ├── api/                    # MAAS API 客户端
│   ├── config/                 # 配置管理
│   ├── services/               # 业务逻辑
│   └── main.py                 # 应用入口
├── tests/                      # 测试套件
├── config.yaml.example         # 示例配置
├── requirements.txt            # 依赖列表
└── README.md                   # 本文档
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=model_comparison_system --cov-report=html
```

## 🐛 故障排除

**问题：所有模型都返回认证错误**
- 解决：检查 `config.yaml` 中的 API 密钥是否正确

**问题：请求超时**
- 解决：增加 `config.yaml` 中的 `timeout` 值

**问题：遇到速率限制**
- 解决：减少 `max_parallel_calls` 或等待几分钟后重试

## 📄 许可证

本项目采用 MIT 许可证。

## 🙏 致谢

- [Gradio](https://gradio.app/) - Web 界面框架
- [MAAS API](https://maas.aiionly.com) - AI 模型访问

---

<div align="center">

Made with ❤️ 

</div>
