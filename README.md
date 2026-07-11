# StarPath Navigator - College Planner

一个基于 AI 的大学生职业规划与学习路线生成工具，以"星际探索"为隐喻，帮助学生从职业推荐、学习路线生成到求职准备，提供一站式职业规划服务。

## 项目特点

- 单页应用，所有页面逻辑在一个 HTML 文件中切换
- 行星可视化：用户为中心恒星，职业为周围行星，大小代表兴趣适配度，距离代表实现难度
- 树状学习路线图：从基础到高级的层层递进学习路径
- 鼠标悬浮显示节点详细信息
- 支持缩放（20%-500%）和拖拽平移
- 用户数据本地存储（localStorage），无后端持久化

## 技术栈

- **前端**：HTML + CSS + 原生 JavaScript（单文件）
- **后端**：Python Flask（单文件）
- **依赖**：flask、requests
- **AI**：DeepSeek API（用于职业推荐和学习路线生成）
- **运行平台**：Windows / macOS / Linux

## 目录结构

```
college-planner/
├── app.py                  # Flask 后端服务（单文件）
├── start.bat               # Windows 启动脚本
├── requirements.txt        # Python 依赖
├── static/
│   └── index.html          # 前端单文件应用（HTML+CSS+JS）
└── venv/                   # Python 虚拟环境
```

## 快速开始

### Windows 系统

双击运行 `start.bat`，脚本会自动：
1. 创建虚拟环境（如果不存在）
2. 安装依赖（flask, requests）
3. 启动 Flask 服务

服务启动后访问：http://localhost:5000

### Linux / macOS 系统

```bash
cd college-planner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

服务启动后访问：http://localhost:5000

## API 接口

### GET /

返回前端页面（`static/index.html`）

### POST /api/recommend

根据用户基本信息推荐职业列表

**请求参数（JSON）**：
| 字段 | 说明 | 必填 |
|------|------|------|
| grade | 年级 | 是 |
| major_category | 专业大类 | 是 |
| major_name | 专业名称 | 是 |
| specialty | 个人特长 | 否 |
| mbti | MBTI 人格 | 否 |
| hobbies | 爱好 | 否 |
| desired_career | 期望职业 | 否 |

**返回**：
```json
{
  "code": 0,
  "data": [
    {"name": "职业名称", "interest_match": 80, "difficulty": 65},
    ...
  ],
  "msg": "success"
}
```

### POST /api/generate

根据用户选择的职业生成详细学习路线图

**请求参数（JSON）**：
| 字段 | 说明 | 必填 |
|------|------|------|
| grade | 年级 | 是 |
| major_category | 专业大类 | 是 |
| major_name | 专业名称 | 是 |
| specialty | 个人特长 | 否 |
| mbti | MBTI 人格 | 否 |
| hobbies | 爱好 | 否 |
| career_name | 目标职业 | 是 |
| custom_questions | 第4步自定义问题答案 | 否 |

**返回**：
```json
{
  "code": 0,
  "data": {
    "nodes": [
      {"id": "start", "name": "当前起点", "type": "start"},
      {"id": "branch1", "name": "前端开发工程师", "type": "branch"},
      ...
      {"id": "end1", "name": "前端架构师", "type": "end"}
    ],
    "connections": [
      {"from": "start", "to": "node1", "difficulty": "简单", "duration": "50小时"},
      ...
    ]
  },
  "msg": "success"
}
```

## 配置 DeepSeek API

本项目使用 DeepSeek AI 提供智能推荐。在 `app.py` 中配置 API Key：

```python
DEEPSEEK_API_KEY = "your-api-key-here"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
```

> 安全建议：生产环境中应将 API Key 存储在环境变量中，不要硬编码到代码中。

## 功能流程

### 1. 填写基本信息
- 年级
- 专业大类
- 专业名称
- 个人特长
- MBTI 人格
- 爱好
- 期望职业

### 2. 选择职业星球
- 系统根据用户信息推荐 10-12 个职业
- 以行星可视化方式展示
- 大小代表兴趣适配度
- 距离代表实现难度
- 用户选择期望职业放在第一位

### 3. 探索内心星球
- 前两个问题：基本信息（职业选择看重因素、应对困难方式）
- 后两个问题：所选星球（选择职业原因、自身优劣势）

### 4. 生成学习路线
- 输入对职业的了解、已学内容、想获得的成就
- 点击"生成学习路线"按钮
- 系统生成详细的学习路线图

### 5. 查看学习路线
- 树状学习路径
- 起点 → 基础学习 → 职业分支点 → 进阶学习 → 高级学习 → 实战项目 → 求职准备 → 终点
- 节点显示学习内容、难度、时长、重要程度
- 悬浮显示详细描述和推荐学习资源

### 6. 查看规划报告
- 包含学习资源汇总
- "去别的星球看看"按钮跳回星图
- "重新输入"按钮重新生成学习路线

## 节点类型说明

| 类型 | 含义 | 样式 |
|------|------|------|
| start | 起点 | 棕色 |
| branch | 职业分支点（具体职业） | 紫色 |
| 普通 | 学习内容节点 | 紫色 |
| end | 终点（细分职业） | 绿色 |

## 学习路线图结构

学习路线遵循"基础 → 进阶 → 高级 → 实践"的层层递进逻辑：

```
起点
├── Python 基础语法与数据结构
├── 数据结构与算法基础
├── MySQL 数据库设计与查询
└── Git 版本控制
        ↓
职业分支点（具体职业）
        ↓
├── HTML/CSS 与 JavaScript
├── Vue3 前端框架
├── TypeScript 进阶
        ↓
├── Django 后端框架
├── RESTful API 设计
├── Redis 缓存技术
        ↓
├── 前端项目实战
├── 后端项目实战
├── Docker 容器化部署
        ↓
├── Linux 服务器操作
├── 作品集与简历优化
        ↓
终点（细分职业）
```

## 安全说明

- DeepSeek API Key 可在配置文件中设置
- 生产环境应使用环境变量存储 API Key
- 所有 AI 生成内容已使用 HTML 转义防止 XSS 漏洞
- 生产环境应禁用 Flask 调试模式

## 浏览器兼容性

- Chrome / Edge 90+
- Firefox 88+
- Safari 14+

## 许可协议

仅供学习和个人使用。

## 常见问题

### Q1: 服务启动失败，提示端口被占用？

修改 `app.py` 最后一行：
```python
app.run(host='0.0.0.0', port=5001, debug=True)  # 改为其他端口
```

### Q2: 启动后访问 5000 端口显示"服务不可用"？

检查终端日志，确认：
- 虚拟环境已正确创建
- 依赖已正确安装
- 端口未被其他程序占用

### Q3: 学习路线图节点显示不完整？

刷新浏览器页面（Ctrl+R）重新生成路线图。

### Q4: AI 返回的节点数量太少？

系统会自动使用备用数据生成完整的学习路线（包含起点+中间节点+终点）。

## 更新日志

### v1.0.0
- 职业推荐与星图可视化
- 学习路线图生成
- 规划报告展示
- 缩放与拖拽平移
- 学习资源汇总
