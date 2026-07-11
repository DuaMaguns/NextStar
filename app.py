from flask import Flask, request, jsonify
import requests
import json
import re
import ast
import os

app = Flask(__name__)


def load_api_key():
    """从环境变量或项目外的 config.json 读取 API Key"""
    # 1. 优先从环境变量读取
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key

    # 2. 从项目外的 config.json 读取（同级目录或上级目录）
    config_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json'),
        os.path.join(os.getcwd(), 'config.json'),
        os.path.join(os.getcwd(), '..', 'config.json'),
    ]
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    key = config.get("deepseek_api_key", "")
                    if key:
                        return key
            except Exception:
                pass

    return ""


DEFAULT_API_KEY = load_api_key()


@app.route('/api/<path:path>', methods=['OPTIONS'])
def options_handler(_path):
    response = app.response_class()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

SYSTEM_PROMPT = """你是专业大学生学业与职业规划顾问，基于学生客观背景与内心价值观输出规划报告，输出分5个板块：方向锚点、适配依据、核心路径、分阶段行动清单、避坑兜底建议。使用Markdown格式，客观务实，不制造焦虑，不替用户做最终选择。"""

CAREER_SUB_DIRECTIONS = {
    "软件工程师": ["前端开发工程师", "后端开发工程师", "全栈开发工程师", "移动端开发工程师", "嵌入式软件工程师"],
    "产品经理": ["产品经理（B端）", "产品经理（C端）", "数据产品经理", "增长产品经理", "AI产品经理"],
    "数据分析师": ["商业数据分析师", "用户行为分析师", "金融数据分析师", "大数据分析师", "量化分析师"],
    "大数据工程师": ["大数据开发工程师", "数据仓库工程师", "ETL工程师", "数据架构师", "实时数据工程师"],
    "人工智能工程师": ["机器学习工程师", "深度学习工程师", "NLP工程师", "计算机视觉工程师", "AI算法工程师"],
    "网络工程师": ["网络安全工程师", "系统运维工程师", "云计算工程师", "DevOps工程师", "IT基础设施工程师"],
    "信息安全分析师": ["渗透测试工程师", "安全运维工程师", "安全架构师", "红队工程师", "安全合规专员"],
    "UI设计师": ["UI设计师", "UX设计师", "交互设计师", "产品设计师", "视觉设计师"],
    "市场营销": ["数字营销专员", "品牌营销经理", "社交媒体运营", "内容营销经理", "营销策划师"],
    "金融分析师": ["投资分析师", "风控分析师", "财务分析师", "资产管理师", "金融顾问"],
    "教师": ["高中教师", "初中教师", "小学教师", "职业教育教师", "教育研究员"],
    "医生": ["内科医生", "外科医生", "儿科医生", "急诊科医生", "专科医生"],
    "律师": ["诉讼律师", "非诉律师", "公司法务", "知识产权律师", "刑事律师"],
    "会计师": ["注册会计师", "管理会计师", "税务会计师", "审计师", "财务顾问"],
    "建筑师": ["建筑设计师", "室内设计师", "景观设计师", "城市规划师", "建筑工程师"],
    "机械工程师": ["机械设计工程师", "智能制造工程师", "自动化工程师", "结构工程师", "设备工程师"],
    "电子工程师": ["硬件工程师", "嵌入式工程师", "集成电路工程师", "PCB工程师", "测试工程师"],
    "创业者": ["科技创业者", "电商创业者", "教育创业者", "文创创业者", "跨境电商创业者"]
}

def get_career_sub_directions(career_name):
    for key in CAREER_SUB_DIRECTIONS:
        if key in career_name or career_name in key:
            return CAREER_SUB_DIRECTIONS[key]
    return ["高级" + career_name, career_name + "专家", career_name + "管理者"]


def call_deepseek(api_key, user_content):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 8000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
    }
    res = requests.post(url, json=payload, headers=headers, timeout=120)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


@app.route('/')
def index():
    with open('static/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    response = app.response_class(content, mimetype='text/html; charset=utf-8')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/recommend', methods=['POST'])
def recommend_careers():
    try:
        data = request.get_json()
        basic_info = data.get('basic_info', {})
        
        if not basic_info:
            return jsonify({"code": -1, "msg": "请填写基础信息"})
        
        desired_career = basic_info.get('desired_career', '').strip()
        
        info_lines = [
            f"- 年级：{basic_info.get('grade', '')}",
            f"- 专业大类：{basic_info.get('major_category', '')}",
            f"- 专业名称：{basic_info.get('major_name', '')}",
            f"- 个人特长：{basic_info.get('skills', '')}",
            f"- 爱好：{basic_info.get('hobbies', '')}",
        ]
        
        if desired_career:
            info_lines.append(f"- 期望职业：{desired_career}")
        
        info_lines.append(f"- MBTI人格：{basic_info.get('mbti', '')}")
        
        requirement_lines = [
            "- **推荐的职业必须与用户的专业高度相关**，如果用户是金融专业，应推荐投资分析师、金融分析师、理财顾问等金融相关职业；如果用户是市场营销专业，应推荐市场营销专员、品牌经理、市场调研专员等营销相关职业",
            "- 推荐的职业应基于用户的专业、特长、爱好等信息进行**客观分析**，推荐真正适合用户的职业",
            "- **推荐的职业应是宏观的职业大类，而不是过于细分的职业方向**（例如：推荐\"软件工程师\"而不是\"前端开发工程师\"，推荐\"设计师\"而不是\"UI设计师\"）",
            "- **禁止推荐与用户专业无关的职业**，例如金融专业的用户不应推荐软件工程师、程序员等计算机相关职业"
        ]
        
        if desired_career:
            requirement_lines.insert(0, f"- 如果用户填写了期望职业\"{desired_career}\"，**必须**将该期望职业作为推荐结果之一，且放在推荐列表的第一位")
            requirement_lines.insert(1, "- 期望职业的兴趣适配度应根据用户实际匹配情况客观评估，不要人为拔高")
            requirement_lines.insert(2, "- 其他推荐职业不必局限于与期望职业相关的领域")
        
        user_content = f"""
学生基础信息：
{'\n'.join(info_lines)}

请根据以上信息，为该学生推荐10-12个适合的职业方向。

**重要要求：**
{'\n'.join(requirement_lines)}

对于每个职业，请提供：
1. 职业名称（应为宏观职业大类）
2. 兴趣适配度（0-100的百分比，表示该职业与用户兴趣、特长的匹配程度）
3. 实现难度（0-100的百分比，表示从当前状态到达该职业的难易程度，难度越高百分比越大）

请使用严格的JSON格式输出，不要包含任何额外文本或Markdown格式。JSON结构如下：
{{
    "careers": [
        {{
            "name": "职业名称",
            "interest_match": 85,
            "difficulty": 60,
            "reason": "简短说明推荐理由"
        }}
    ]
}}
"""
        
        result = call_deepseek(DEFAULT_API_KEY, user_content)
        
        try:
            json_result = json.loads(result)
        except json.JSONDecodeError:
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end != -1:
                json_result = json.loads(result[start:end])
            else:
                raise ValueError("无法解析返回的JSON数据")
        
        return jsonify({"code": 0, "data": json_result, "msg": "success"})
    
    except Exception as e:
        return generate_fallback_careers(basic_info)


def generate_fallback_careers(basic_info):
    default_careers = [
        {"name": "软件工程师", "interest_match": 80, "difficulty": 65, "reason": "适合有编程兴趣和逻辑思维能力的学生"},
        {"name": "产品经理", "interest_match": 75, "difficulty": 50, "reason": "适合善于沟通、有创意和用户思维的学生"},
        {"name": "设计师", "interest_match": 70, "difficulty": 60, "reason": "适合有艺术天赋和审美能力的学生"},
        {"name": "数据分析师", "interest_match": 75, "difficulty": 65, "reason": "适合擅长数学、统计和逻辑分析的学生"},
        {"name": "市场营销专员", "interest_match": 65, "difficulty": 45, "reason": "适合善于沟通、有创意和市场敏感度的学生"},
        {"name": "运营专员", "interest_match": 60, "difficulty": 40, "reason": "适合执行力强、善于数据分析的学生"},
        {"name": "创业家", "interest_match": 70, "difficulty": 85, "reason": "适合有商业头脑、敢于创新和承担风险的学生"},
        {"name": "教育工作者", "interest_match": 60, "difficulty": 55, "reason": "适合热爱教育、善于表达和有耐心的学生"},
        {"name": "咨询师", "interest_match": 65, "difficulty": 70, "reason": "适合逻辑清晰、善于分析和沟通的学生"},
        {"name": "内容创作者", "interest_match": 70, "difficulty": 55, "reason": "适合有创作热情和表达能力的学生"},
        {"name": "游戏设计师", "interest_match": 75, "difficulty": 70, "reason": "适合热爱游戏、有创意和技术能力的学生"},
        {"name": "网络安全工程师", "interest_match": 65, "difficulty": 80, "reason": "适合细心、有耐心和技术能力的学生"}
    ]
    
    desired_career = basic_info.get('desired_career', '').strip()
    if desired_career:
        for career in default_careers:
            if career['name'] == desired_career:
                default_careers.remove(career)
                default_careers.insert(0, career)
                break
        else:
            default_careers.insert(0, {"name": desired_career, "interest_match": 85, "difficulty": 60, "reason": "用户期望职业"})
    
    major_category = basic_info.get('major_category', '')
    skills = basic_info.get('skills', '')
    hobbies = basic_info.get('hobbies', '')
    
    tech_keywords = ['计算机', '软件', '编程', '技术', '数据', '信息']
    design_keywords = ['设计', '艺术', '美术', '创意']
    business_keywords = ['管理', '经济', '营销', '商业']
    education_keywords = ['教育', '师范', '心理']
    
    if any(kw in major_category for kw in tech_keywords) or any(kw in skills for kw in tech_keywords):
        for career in default_careers:
            if career['name'] in ['软件工程师', '数据分析师', '网络安全工程师', '游戏设计师']:
                career['interest_match'] = min(95, career['interest_match'] + 10)
    elif any(kw in major_category for kw in design_keywords) or any(kw in hobbies for kw in design_keywords):
        for career in default_careers:
            if career['name'] in ['设计师', '内容创作者', '游戏设计师']:
                career['interest_match'] = min(95, career['interest_match'] + 10)
    elif any(kw in major_category for kw in business_keywords) or any(kw in skills for kw in business_keywords):
        for career in default_careers:
            if career['name'] in ['产品经理', '市场营销专员', '创业家', '咨询师']:
                career['interest_match'] = min(95, career['interest_match'] + 10)
    elif any(kw in major_category for kw in education_keywords):
        for career in default_careers:
            if career['name'] in ['教育工作者', '咨询师']:
                career['interest_match'] = min(95, career['interest_match'] + 10)
    
    return jsonify({"code": 0, "data": {"careers": default_careers}, "msg": "使用默认推荐数据"})


@app.route('/api/generate', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        
        basic_info = data.get('basic_info', {})
        deep_answers = data.get('deep_answers', [])
        
        if not basic_info:
            return jsonify({"code": -1, "msg": "请填写基础信息"})
        
        desired_career = basic_info.get('desired_career', '').strip()
        
        info_lines = [
            f"- 年级：{basic_info.get('grade', '')}",
            f"- 专业大类：{basic_info.get('major_category', '')}",
            f"- 专业名称：{basic_info.get('major_name', '')}",
            f"- 个人特长：{basic_info.get('skills', '')}",
            f"- 爱好：{basic_info.get('hobbies', '')}",
        ]
        
        if desired_career:
            info_lines.append(f"- 期望职业：{desired_career}")
        
        info_lines.append(f"- MBTI人格：{basic_info.get('mbti', '')}")
        
        user_content = f"""
学生基础信息：
{'\n'.join(info_lines)}

深层价值观探索回答：
"""
        for i, answer in enumerate(deep_answers, 1):
            user_content += f"- 问题{i}：{answer}\n"
        
        user_content += """
        
请根据以上信息，为该学生生成一份专业的学业与职业规划报告。报告需包含以下5个板块：
1. 方向锚点：基于喜欢、擅长、有价值三要素，推荐最适配的职业发展方向
2. 适配依据：详细说明推荐方向的匹配理由
3. 核心路径：从当前年级出发的主要发展路径
4. 分阶段行动清单：按时间周期（学期/学年）规划具体行动步骤
5. 避坑兜底建议：可能遇到的挑战及备选方案

请使用Markdown格式输出，语言温和务实，不制造焦虑。
"""
        
        result = call_deepseek(DEFAULT_API_KEY, user_content)
        
        return jsonify({"code": 0, "data": result, "msg": "success"})
    
    except Exception as e:
        return jsonify({"code": -1, "msg": f"生成报告失败：{str(e)}"})


@app.route('/api/learning_path', methods=['POST'])
def generate_learning_path():
    career_name = ''
    try:
        data = request.get_json()
        
        basic_info = data.get('basic_info', {})
        career_name = data.get('career_name', '')
        career_knowledge = data.get('career_knowledge', '')
        career_skills = data.get('career_skills', '')
        career_goals = data.get('career_goals', '')
        
        if not career_name:
            return jsonify({"code": -1, "msg": "请选择职业"})
        
        user_content = f"""
学生基础信息：
- 年级：{basic_info.get('grade', '')}
- 专业大类：{basic_info.get('major_category', '')}
- 专业名称：{basic_info.get('major_name', '')}
- 个人特长：{basic_info.get('skills', '')}
- 爱好：{basic_info.get('hobbies', '')}
- MBTI人格：{basic_info.get('mbti', '')}

目标职业：{career_name}

用户对该职业的了解：{career_knowledge}

用户已掌握的技能：{career_skills}

用户想获得的成就：{career_goals}

## 核心指令（必须严格遵守）

你是一名专业的学习规划师。请根据以上用户信息，为用户生成一份与专业和职业**高度匹配**的学习路线图。

### 关键原则：内容必须与专业和职业相关
- **禁止生成与用户专业和目标职业无关的学习内容**
- 如果用户是金融专业，学习内容必须是金融相关的（如经济学、会计学、投资分析等），不要出现Python编程、数据库、前端开发等计算机内容
- 如果用户是市场营销专业，学习内容必须是营销相关的（如消费者行为学、市场调研、品牌营销等），不要出现编程、算法等计算机内容
- 如果用户是设计专业，学习内容必须是设计相关的（如设计基础、色彩理论、UI设计等），不要出现编程、数据结构等计算机内容
- 如果用户是计算机相关专业，才可以生成编程、算法、数据库等计算机内容

### 结构要求：循环图结构
学习路线图**必须呈现循环图（有环图）结构**，允许节点有多个父节点和子节点，支持循环连接。

### 学习阶段示例（根据专业选择对应内容）

**金融/经济类专业示例：**
- 基础层：经济学原理、会计学基础、统计学基础、金融市场概论、货币银行学
- 进阶层：投资分析、金融建模、风险管理、金融工程、财务报表分析
- 高级层：量化投资策略、金融衍生品定价、资产组合管理、金融科技应用
- 实践层：金融实习、投资组合构建、金融案例分析、求职准备

**市场营销类专业示例：**
- 基础层：市场营销原理、消费者行为学、市场调研方法、广告学基础、品牌管理概论
- 进阶层：数字营销、社交媒体营销、营销数据分析、内容营销、营销策划
- 高级层：整合营销传播、营销战略规划、客户关系管理、营销ROI分析
- 实践层：营销项目实践、品牌策划实战、市场调研项目、求职准备

**设计类专业示例：**
- 基础层：设计基础、色彩理论、构成原理、手绘基础、设计工具基础
- 进阶层：UI设计、交互设计、用户研究、设计规范、设计系统
- 高级层：设计策略、设计管理、设计思维、设计趋势研究
- 实践层：设计项目实战、作品集制作、设计竞赛、求职准备

**计算机/技术类专业示例：**
- 基础层：编程语言基础、数据结构与算法、数据库原理、计算机网络基础、操作系统原理
- 进阶层：专业技术框架、系统设计、工程化实践、性能优化、安全开发
- 高级层：分布式系统、微服务架构、云计算、人工智能、技术架构设计
- 实践层：项目开发实战、技术博客写作、开源贡献、求职准备

### 节点数据要求
每个节点必须包含：
- id：唯一标识符（如"start"、"node1"、"branch1"、"end1"）
- name：具体学习内容名称或职业名称（必须非常具体）
- difficulty：难度（1-5数字）
- duration：学习时长（预计小时数）
- importance：重要程度（1-5数字）
- description：详细描述（40-80字），说明具体学习内容、目标、方法
- resources：推荐学习资源数组，**至少包含3个资源**，其中**至少2个是B站教学视频**，每个资源包含name（具体课程/书籍名称）和url（搜索链接）
- type："start"表示起点，"end"表示终点

### 资源格式要求
- B站视频链接格式：`https://search.bilibili.com/all?keyword=具体搜索关键词`
- 书籍链接格式：`https://book.douban.com/subject_search?search_text=书籍名称`
- MOOC课程链接格式：`https://www.icourse163.org/search.htm?search=课程名称`
- 知乎文章链接格式：`https://www.zhihu.com/search?type=content&q=搜索关键词`

### 连接关系要求
- 必须形成循环图结构，允许循环连接和交叉连接
- 分支点必须是具体的职业名称
- 终点必须是具体的细分职业名称
- 总节点数至少12个

### 输出格式
返回纯JSON格式，结构如下：

```json
{{
    "nodes": [...],
    "connections": [...]
}}
```

**请确保学习内容与用户的专业和目标职业完全匹配，不要出现任何无关的内容！**
"""
        
        result = call_deepseek(DEFAULT_API_KEY, user_content)
        
        json_result = None
        try:
            cleaned_result = result.strip()
            cleaned_result = re.sub(r'^```json\s*', '', cleaned_result)
            cleaned_result = re.sub(r'\s*```\s*$', '', cleaned_result)
            cleaned_result = re.sub(r'//.*?$', '', cleaned_result, flags=re.MULTILINE)
            cleaned_result = re.sub(r'/\*.*?\*/', '', cleaned_result, flags=re.DOTALL)
            cleaned_result = cleaned_result.strip()
            
            json_result = json.loads(cleaned_result)
        except json.JSONDecodeError:
            try:
                start = result.find('{')
                end = result.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = result[start:end]
                    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                    json_str = re.sub(r'```json\s*', '', json_str)
                    json_str = re.sub(r'\s*```\s*$', '', json_str)
                    json_str = json_str.strip()
                    json_result = json.loads(json_str)
            except Exception:
                try:
                    json_str = result[result.find('{'):result.rfind('}') + 1]
                    json_str = re.sub(r'```json\s*', '', json_str)
                    json_str = re.sub(r'\s*```\s*$', '', json_str)
                    json_str = json_str.strip()
                    json_result = ast.literal_eval(json_str)
                except Exception:
                    pass
        
        if json_result is None:
            json_result = generate_fallback_learning_path(career_name)
        else:
            json_result = validate_and_enhance_learning_path(json_result, career_name)
        
        response = jsonify({"code": 0, "data": json_result, "msg": "success"})
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    except Exception as e:
        fallback_result = generate_fallback_learning_path(career_name)
        response = jsonify({
            "code": 0, 
            "data": fallback_result, 
            "msg": f"生成学习路线失败，已使用默认路线：{str(e)}"
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response


def generate_fallback_learning_path(career_name):
    tech_keywords = ['软件', '工程师', '开发', '程序员', '编程', '技术', '算法', '数据', '计算机', '前端', '后端', '全栈']
    design_keywords = ['设计', '设计师', '视觉', '插画', 'UI', 'UX', '交互', '产品设计']
    education_keywords = ['教育', '教师', '培训', '讲师']
    finance_keywords = ['金融', '投资', '银行', '证券', '保险', '基金', '理财']
    marketing_keywords = ['营销', '市场', '品牌', '广告', '推广', '公关']
    
    branch_professions = []
    end_professions = []
    learning_nodes = []
    connections = []
    
    if any(kw in career_name for kw in tech_keywords):
        branch_professions = [
            {"name": "前端开发工程师", "id": "branch1", "desc": "专注用户界面开发"},
            {"name": "后端开发工程师", "id": "branch2", "desc": "专注服务端开发"},
            {"name": "全栈开发工程师", "id": "branch3", "desc": "掌握前后端技术"}
        ]
        end_professions = [
            {"name": "前端架构师", "desc": "主导前端技术架构"},
            {"name": "后端技术专家", "desc": "深耕后端技术"},
            {"name": "全栈技术负责人", "desc": "统筹全栈技术方案"},
            {"name": "数据算法工程师", "desc": "专注数据分析和算法"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "学习Python基础语法", "difficulty": 2, "duration": 50, "importance": 5,
             "resources": [{"name": "B站：Python零基础入门教程", "url": "https://search.bilibili.com/all?keyword=Python零基础入门教程"}],
             "description": "系统学习Python基础语法"},
            {"id": "node2", "name": "掌握数据结构与算法", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：算法导论", "url": "https://book.douban.com/subject_search?search_text=算法导论"}],
             "description": "学习数据结构和算法"},
            {"id": "node3", "name": "学习MySQL数据库", "difficulty": 3, "duration": 40, "importance": 5,
             "resources": [{"name": "B站：MySQL数据库入门教程", "url": "https://search.bilibili.com/all?keyword=MySQL数据库入门教程"}],
             "description": "掌握数据库原理和SQL"},
            {"id": "node5", "name": "掌握Git版本控制", "difficulty": 2, "duration": 20, "importance": 4,
             "resources": [{"name": "GitHub：官方文档", "url": "https://github.com/git-guides"}],
             "description": "学习Git版本控制"},
            {"id": "node6a", "name": "学习HTML/CSS/JavaScript", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "MDN：Web开发指南", "url": "https://developer.mozilla.org/zh-CN/docs/Learn"}],
             "description": "学习前端开发基础"},
            {"id": "node6b", "name": "学习Vue3框架", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "Vue官方文档", "url": "https://cn.vuejs.org/"}],
             "description": "掌握Vue3前端框架"},
            {"id": "node7a", "name": "学习Django框架", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "Django官方文档", "url": "https://docs.djangoproject.com/zh-hans/"}],
             "description": "学习后端开发框架"},
            {"id": "node8a", "name": "前端项目实战", "difficulty": 5, "duration": 100, "importance": 5,
             "resources": [{"name": "GitHub：前端实战项目", "url": "https://github.com/search?q=frontend+project"}],
             "description": "参与前端项目开发"},
            {"id": "node8b", "name": "后端项目实战", "difficulty": 5, "duration": 100, "importance": 5,
             "resources": [{"name": "GitHub：后端实战项目", "url": "https://github.com/search?q=backend+project"}],
             "description": "参与后端项目开发"},
            {"id": "node10", "name": "作品集与简历优化", "difficulty": 4, "duration": 40, "importance": 5,
             "resources": [{"name": "知乎：技术面试经验", "url": "https://www.zhihu.com/search?type=content&q=技术面试经验"}],
             "description": "准备求职材料"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "start", "to": "node2"},
            {"from": "start", "to": "node3"}, {"from": "start", "to": "node5"},
            {"from": "node1", "to": "branch1"}, {"from": "node1", "to": "branch2"},
            {"from": "node1", "to": "branch3"}, {"from": "node2", "to": "branch1"},
            {"from": "node2", "to": "branch2"}, {"from": "node2", "to": "branch3"},
            {"from": "branch1", "to": "node6a"}, {"from": "node6a", "to": "node6b"},
            {"from": "branch2", "to": "node7a"}, {"from": "branch3", "to": "node6a"},
            {"from": "branch3", "to": "node7a"}, {"from": "node6b", "to": "node8a"},
            {"from": "node7a", "to": "node8b"}, {"from": "node8a", "to": "node10"},
            {"from": "node8b", "to": "node10"}, {"from": "node10", "to": "end1"},
            {"from": "node10", "to": "end2"}, {"from": "node10", "to": "end3"},
            {"from": "node10", "to": "end4"}
        ]
        
    elif any(kw in career_name for kw in finance_keywords):
        branch_professions = [
            {"name": "投资分析师", "id": "branch1", "desc": "专注投资分析和研究"},
            {"name": "金融分析师", "id": "branch2", "desc": "专注财务分析和估值"},
            {"name": "理财顾问", "id": "branch3", "desc": "为客户提供理财建议"}
        ]
        end_professions = [
            {"name": "资深投资分析师", "desc": "主导投资研究和决策"},
            {"name": "金融衍生品专家", "desc": "精通金融衍生品定价"},
            {"name": "财富管理总监", "desc": "统筹财富管理业务"},
            {"name": "量化投资策略师", "desc": "开发量化投资策略"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "经济学原理", "difficulty": 2, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：经济学原理", "url": "https://book.douban.com/subject_search?search_text=经济学原理"}],
             "description": "学习宏观和微观经济学基础"},
            {"id": "node2", "name": "会计学基础", "difficulty": 3, "duration": 80, "importance": 5,
             "resources": [{"name": "MOOC：会计学基础", "url": "https://www.icourse163.org/search.htm?search=会计学基础"}],
             "description": "掌握会计核算和财务报表"},
            {"id": "node3", "name": "统计学基础", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：统计学导论", "url": "https://book.douban.com/subject_search?search_text=统计学导论"}],
             "description": "学习统计方法和数据分析"},
            {"id": "node5", "name": "金融市场概论", "difficulty": 2, "duration": 40, "importance": 5,
             "resources": [{"name": "B站：金融市场入门", "url": "https://search.bilibili.com/all?keyword=金融市场入门"}],
             "description": "了解金融市场结构和运作"},
            {"id": "node6a", "name": "投资分析与组合管理", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "书籍：投资学", "url": "https://book.douban.com/subject_search?search_text=投资学"}],
             "description": "学习投资分析方法和组合构建"},
            {"id": "node6b", "name": "金融建模与估值", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "书籍：财务报表分析", "url": "https://book.douban.com/subject_search?search_text=财务报表分析"}],
             "description": "掌握金融建模和企业估值"},
            {"id": "node7a", "name": "风险管理", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "MOOC：风险管理", "url": "https://www.icourse163.org/search.htm?search=风险管理"}],
             "description": "学习风险识别和管理策略"},
            {"id": "node8a", "name": "金融实习实践", "difficulty": 5, "duration": 120, "importance": 5,
             "resources": [{"name": "知乎：金融实习经验", "url": "https://www.zhihu.com/search?type=content&q=金融实习经验"}],
             "description": "参与金融机构实习"},
            {"id": "node10", "name": "CFA考试准备", "difficulty": 5, "duration": 100, "importance": 5,
             "resources": [{"name": "CFA官方教材", "url": "https://www.cfainstitute.org/"}],
             "description": "准备CFA资格考试"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "start", "to": "node2"},
            {"from": "start", "to": "node3"}, {"from": "start", "to": "node5"},
            {"from": "node1", "to": "branch1"}, {"from": "node1", "to": "branch2"},
            {"from": "node1", "to": "branch3"}, {"from": "node2", "to": "branch2"},
            {"from": "node3", "to": "branch1"}, {"from": "branch1", "to": "node6a"},
            {"from": "branch2", "to": "node6b"}, {"from": "branch3", "to": "node7a"},
            {"from": "node6a", "to": "node8a"}, {"from": "node6b", "to": "node8a"},
            {"from": "node7a", "to": "node8a"}, {"from": "node8a", "to": "node10"},
            {"from": "node10", "to": "end1"}, {"from": "node10", "to": "end2"},
            {"from": "node10", "to": "end3"}, {"from": "node10", "to": "end4"}
        ]
        
    elif any(kw in career_name for kw in marketing_keywords):
        branch_professions = [
            {"name": "市场营销专员", "id": "branch1", "desc": "制定营销策略"},
            {"name": "品牌经理", "id": "branch2", "desc": "管理品牌形象"},
            {"name": "数字营销专员", "id": "branch3", "desc": "负责数字营销"}
        ]
        end_professions = [
            {"name": "市场总监", "desc": "统筹市场战略"},
            {"name": "品牌总监", "desc": "主导品牌发展"},
            {"name": "数字营销专家", "desc": "精通数字营销技术"},
            {"name": "营销策划总监", "desc": "统筹营销策划"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "市场营销原理", "difficulty": 2, "duration": 50, "importance": 5,
             "resources": [{"name": "书籍：市场营销原理", "url": "https://book.douban.com/subject_search?search_text=市场营销原理"}],
             "description": "学习市场营销基本理论"},
            {"id": "node2", "name": "消费者行为学", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：消费者行为学", "url": "https://book.douban.com/subject_search?search_text=消费者行为学"}],
             "description": "了解消费者心理和行为"},
            {"id": "node3", "name": "市场调研方法", "difficulty": 3, "duration": 50, "importance": 5,
             "resources": [{"name": "MOOC：市场调研", "url": "https://www.icourse163.org/search.htm?search=市场调研"}],
             "description": "掌握市场调研技术"},
            {"id": "node5", "name": "广告学基础", "difficulty": 2, "duration": 40, "importance": 4,
             "resources": [{"name": "B站：广告学入门", "url": "https://search.bilibili.com/all?keyword=广告学入门"}],
             "description": "学习广告理论和实践"},
            {"id": "node6a", "name": "社交媒体营销", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "知乎：社交媒体营销", "url": "https://www.zhihu.com/search?type=content&q=社交媒体营销"}],
             "description": "学习社交媒体运营"},
            {"id": "node6b", "name": "营销数据分析", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "MOOC：营销数据分析", "url": "https://www.icourse163.org/search.htm?search=营销数据分析"}],
             "description": "掌握营销数据处理"},
            {"id": "node7a", "name": "品牌管理", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：品牌管理", "url": "https://book.douban.com/subject_search?search_text=品牌管理"}],
             "description": "学习品牌策略和管理"},
            {"id": "node8a", "name": "营销项目实战", "difficulty": 5, "duration": 100, "importance": 5,
             "resources": [{"name": "知乎：营销项目经验", "url": "https://www.zhihu.com/search?type=content&q=营销项目经验"}],
             "description": "参与真实营销项目"},
            {"id": "node10", "name": "营销作品集准备", "difficulty": 4, "duration": 40, "importance": 5,
             "resources": [{"name": "B站：营销简历技巧", "url": "https://search.bilibili.com/all?keyword=营销简历技巧"}],
             "description": "准备求职材料"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "start", "to": "node2"},
            {"from": "start", "to": "node3"}, {"from": "start", "to": "node5"},
            {"from": "node1", "to": "branch1"}, {"from": "node1", "to": "branch2"},
            {"from": "node1", "to": "branch3"}, {"from": "node2", "to": "branch1"},
            {"from": "node3", "to": "branch1"}, {"from": "branch1", "to": "node6a"},
            {"from": "branch2", "to": "node7a"}, {"from": "branch3", "to": "node6b"},
            {"from": "node6a", "to": "node8a"}, {"from": "node6b", "to": "node8a"},
            {"from": "node7a", "to": "node8a"}, {"from": "node8a", "to": "node10"},
            {"from": "node10", "to": "end1"}, {"from": "node10", "to": "end2"},
            {"from": "node10", "to": "end3"}, {"from": "node10", "to": "end4"}
        ]
        
    elif any(kw in career_name for kw in design_keywords):
        branch_professions = [
            {"name": "UI设计师", "id": "branch1", "desc": "专注用户界面设计"},
            {"name": "UX设计师", "id": "branch2", "desc": "专注用户体验"},
            {"name": "品牌设计师", "id": "branch3", "desc": "专注品牌视觉"}
        ]
        end_professions = [
            {"name": "设计总监", "desc": "主导设计团队"},
            {"name": "产品设计专家", "desc": "整合设计与商业"},
            {"name": "插画艺术家", "desc": "专注插画创作"},
            {"name": "交互设计师", "desc": "专注交互设计"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "设计基础", "difficulty": 2, "duration": 50, "importance": 5,
             "resources": [{"name": "书籍：设计基础", "url": "https://book.douban.com/subject_search?search_text=设计基础"}],
             "description": "学习设计基本理论"},
            {"id": "node2", "name": "色彩理论", "difficulty": 3, "duration": 40, "importance": 5,
             "resources": [{"name": "B站：色彩理论教程", "url": "https://search.bilibili.com/all?keyword=色彩理论教程"}],
             "description": "掌握色彩搭配原则"},
            {"id": "node3", "name": "构成原理", "difficulty": 3, "duration": 50, "importance": 5,
             "resources": [{"name": "书籍：构成设计", "url": "https://book.douban.com/subject_search?search_text=构成设计"}],
             "description": "学习平面构成和立体构成"},
            {"id": "node5", "name": "手绘基础", "difficulty": 2, "duration": 60, "importance": 4,
             "resources": [{"name": "B站：手绘入门教程", "url": "https://search.bilibili.com/all?keyword=手绘入门教程"}],
             "description": "练习手绘表达能力"},
            {"id": "node6a", "name": "UI设计实战", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "B站：UI设计教程", "url": "https://search.bilibili.com/all?keyword=UI设计教程"}],
             "description": "学习界面设计技巧"},
            {"id": "node6b", "name": "交互设计", "difficulty": 4, "duration": 80, "importance": 5,
             "resources": [{"name": "书籍：交互设计精髓", "url": "https://book.douban.com/subject_search?search_text=交互设计精髓"}],
             "description": "掌握交互设计方法"},
            {"id": "node7a", "name": "设计工具精通", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "Figma官方教程", "url": "https://www.figma.com/learn/"}],
             "description": "精通设计软件"},
            {"id": "node8a", "name": "设计项目实战", "difficulty": 5, "duration": 100, "importance": 5,
             "resources": [{"name": "Dribbble：优秀设计作品", "url": "https://dribbble.com/"}, {"name": "Behance：设计作品集", "url": "https://www.behance.net/"}],
             "description": "参与设计项目"},
            {"id": "node10", "name": "作品集制作", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "知乎：设计作品集", "url": "https://www.zhihu.com/search?type=content&q=设计作品集"}],
             "description": "制作个人作品集"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "start", "to": "node2"},
            {"from": "start", "to": "node3"}, {"from": "start", "to": "node5"},
            {"from": "node1", "to": "branch1"}, {"from": "node1", "to": "branch2"},
            {"from": "node1", "to": "branch3"}, {"from": "node2", "to": "branch1"},
            {"from": "branch1", "to": "node6a"}, {"from": "branch2", "to": "node6b"},
            {"from": "branch3", "to": "node7a"}, {"from": "node6a", "to": "node8a"},
            {"from": "node6b", "to": "node8a"}, {"from": "node7a", "to": "node8a"},
            {"from": "node8a", "to": "node10"}, {"from": "node10", "to": "end1"},
            {"from": "node10", "to": "end2"}, {"from": "node10", "to": "end3"},
            {"from": "node10", "to": "end4"}
        ]
        
    elif any(kw in career_name for kw in education_keywords):
        branch_professions = [
            {"name": "学校教师", "id": "branch1", "desc": "在学校从事教学"},
            {"name": "在线教育讲师", "id": "branch2", "desc": "开发在线课程"},
            {"name": "职业培训师", "id": "branch3", "desc": "提供职业培训"}
        ]
        end_professions = [
            {"name": "高级教师", "desc": "成为学科带头人"},
            {"name": "教育产品经理", "desc": "设计教育产品"},
            {"name": "教育机构负责人", "desc": "管理教育机构"},
            {"name": "教育技术专家", "desc": "推动教育创新"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "教育学原理", "difficulty": 2, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：教育学原理", "url": "https://book.douban.com/subject_search?search_text=教育学原理"}],
             "description": "学习教育基本理论"},
            {"id": "node2", "name": "教育心理学", "difficulty": 3, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：教育心理学", "url": "https://book.douban.com/subject_search?search_text=教育心理学"}],
             "description": "了解学生心理发展"},
            {"id": "node3", "name": "教学方法", "difficulty": 3, "duration": 50, "importance": 5,
             "resources": [{"name": "MOOC：教学方法", "url": "https://www.icourse163.org/search.htm?search=教学方法"}],
             "description": "掌握教学策略和方法"},
            {"id": "node5", "name": "课程设计", "difficulty": 3, "duration": 50, "importance": 5,
             "resources": [{"name": "书籍：课程设计", "url": "https://book.douban.com/subject_search?search_text=课程设计"}],
             "description": "学习课程开发设计"},
            {"id": "node6a", "name": "课堂管理", "difficulty": 3, "duration": 40, "importance": 5,
             "resources": [{"name": "知乎：课堂管理", "url": "https://www.zhihu.com/search?type=content&q=课堂管理"}],
             "description": "掌握课堂管理技巧"},
            {"id": "node6b", "name": "教育技术应用", "difficulty": 3, "duration": 50, "importance": 4,
             "resources": [{"name": "MOOC：教育技术", "url": "https://www.icourse163.org/search.htm?search=教育技术"}],
             "description": "学习教育技术工具"},
            {"id": "node7a", "name": "教育评估", "difficulty": 4, "duration": 50, "importance": 5,
             "resources": [{"name": "书籍：教育测量与评价", "url": "https://book.douban.com/subject_search?search_text=教育测量与评价"}],
             "description": "掌握教育评价方法"},
            {"id": "node8a", "name": "教育实习", "difficulty": 5, "duration": 120, "importance": 5,
             "resources": [{"name": "知乎：教育实习经验", "url": "https://www.zhihu.com/search?type=content&q=教育实习经验"}],
             "description": "参与教育实习"},
            {"id": "node10", "name": "教师资格证考试", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "B站：教师资格证教程", "url": "https://search.bilibili.com/all?keyword=教师资格证教程"}],
             "description": "准备教师资格考试"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "start", "to": "node2"},
            {"from": "start", "to": "node3"}, {"from": "start", "to": "node5"},
            {"from": "node1", "to": "branch1"}, {"from": "node1", "to": "branch2"},
            {"from": "node1", "to": "branch3"}, {"from": "node2", "to": "branch1"},
            {"from": "branch1", "to": "node6a"}, {"from": "branch2", "to": "node6b"},
            {"from": "branch3", "to": "node7a"}, {"from": "node6a", "to": "node8a"},
            {"from": "node6b", "to": "node8a"}, {"from": "node7a", "to": "node8a"},
            {"from": "node8a", "to": "node10"}, {"from": "node10", "to": "end1"},
            {"from": "node10", "to": "end2"}, {"from": "node10", "to": "end3"},
            {"from": "node10", "to": "end4"}
        ]
        
    else:
        branch_professions = [
            {"name": career_name + "（技术方向）", "id": "branch1", "desc": "深耕专业技术"},
            {"name": career_name + "（管理方向）", "id": "branch2", "desc": "走向管理岗位"},
            {"name": career_name + "（创业方向）", "id": "branch3", "desc": "实现商业价值"}
        ]
        end_professions = [
            {"name": career_name + "（高级专家）", "desc": "成为行业权威"},
            {"name": career_name + "（团队负责人）", "desc": "带领团队发展"},
            {"name": career_name + "（创业者）", "desc": "创办企业"},
            {"name": career_name + "（行业顾问）", "desc": "提供专业咨询"}
        ]
        learning_nodes = [
            {"id": "node1", "name": "专业基础理论", "difficulty": 2, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：专业导论", "url": "https://book.douban.com/subject_search?search_text=专业导论"}],
             "description": "学习专业基础理论"},
            {"id": "node2", "name": "核心技能训练", "difficulty": 3, "duration": 80, "importance": 5,
             "resources": [{"name": "MOOC：专业技能", "url": "https://www.icourse163.org/search.htm?search=专业技能"}],
             "description": "掌握专业核心技能"},
            {"id": "node3", "name": "行业实践", "difficulty": 4, "duration": 100, "importance": 5,
             "resources": [{"name": "知乎：行业经验", "url": "https://www.zhihu.com/search?type=content&q=行业经验"}],
             "description": "参与行业实践"},
            {"id": "node10", "name": "职业资格准备", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "B站：职业资格考试", "url": "https://search.bilibili.com/all?keyword=职业资格考试"}],
             "description": "准备职业资格认证"}
        ]
        connections = [
            {"from": "start", "to": "node1"}, {"from": "node1", "to": "node2"},
            {"from": "node2", "to": "branch1"}, {"from": "node2", "to": "branch2"},
            {"from": "node2", "to": "branch3"}, {"from": "branch1", "to": "node3"},
            {"from": "branch2", "to": "node3"}, {"from": "branch3", "to": "node3"},
            {"from": "node3", "to": "node10"}, {"from": "node10", "to": "end1"},
            {"from": "node10", "to": "end2"}, {"from": "node10", "to": "end3"},
            {"from": "node10", "to": "end4"}
        ]
    
    nodes = [
        {"id": "start", "name": "当前起点", "type": "start", "description": "你的当前知识水平和学习起点"}
    ]
    
    nodes.extend(learning_nodes)
    
    nodes.extend([
        {"id": branch_professions[0]["id"], "name": branch_professions[0]["name"], "type": "branch",
         "description": branch_professions[0]["desc"], "difficulty": 4, "duration": 80, "importance": 5},
        {"id": branch_professions[1]["id"], "name": branch_professions[1]["name"], "type": "branch",
         "description": branch_professions[1]["desc"], "difficulty": 4, "duration": 80, "importance": 5},
        {"id": branch_professions[2]["id"], "name": branch_professions[2]["name"], "type": "branch",
         "description": branch_professions[2]["desc"], "difficulty": 4, "duration": 80, "importance": 5},
        {"id": "end1", "name": end_professions[0]["name"], "type": "end", "description": end_professions[0]["desc"]},
        {"id": "end2", "name": end_professions[1]["name"], "type": "end", "description": end_professions[1]["desc"]},
        {"id": "end3", "name": end_professions[2]["name"], "type": "end", "description": end_professions[2]["desc"]},
        {"id": "end4", "name": end_professions[3]["name"], "type": "end", "description": end_professions[3]["desc"]}
    ])
    
    return {
        "nodes": nodes,
        "connections": connections
    }

def sanitize_resource_urls(nodes):
    url_pattern = re.compile(r'^https?://[^\s<>"\']+$')
    
    for node in nodes:
        if not node.get('resources'):
            continue
        
        sanitized_resources = []
        seen_urls = set()
        
        for resource in node['resources']:
            if isinstance(resource, dict):
                name = resource.get('name', '')
                url = resource.get('url', '')
                if not url or not url_pattern.match(url):
                    continue
                if not name:
                    name = extract_resource_name_from_url(url)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                sanitized_resources.append({"name": name, "url": url})
            elif isinstance(resource, str):
                url_match = re.search(r'https?://[^\s<>"\']+', resource)
                if not url_match:
                    continue
                url = url_match.group(0)
                if not url_pattern.match(url):
                    continue
                text_before = resource[:url_match.start()].strip()
                name = text_before or extract_resource_name_from_url(url)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                sanitized_resources.append({"name": name, "url": url})
        
        node['resources'] = sanitized_resources


def extract_resource_name_from_url(url):
    if 'bilibili.com' in url:
        return 'B站视频'
    if 'xuetangx.com' in url or 'icourse163.org' in url:
        return 'MOOC课程'
    if 'book.douban.com' in url:
        return '书籍/教材'
    if 'github.com' in url:
        return '代码仓库'
    if 'zhihu.com' in url:
        return '知乎文章'
    if 'coursera.org' in url:
        return '在线课程'
    return '学习资源'


def validate_and_enhance_learning_path(data, career_name):
    if not data or not data.get('nodes') or not data.get('connections'):
        return generate_fallback_learning_path(career_name)
    
    nodes = data['nodes']
    connections = data['connections']
    
    sanitize_resource_urls(nodes)
    
    node_count = len(nodes)
    end_nodes = [n for n in nodes if n.get('type') == 'end']
    middle_nodes = [n for n in nodes if n.get('type') not in ['start', 'end']]
    
    if node_count < 6:
        return generate_fallback_learning_path(career_name)
    
    if len(end_nodes) < 3:
        existing_end_ids = set(n['id'] for n in end_nodes)
        existing_end_names = set(n['name'] for n in end_nodes)
        sub_directions = get_career_sub_directions(career_name)
        for i in range(len(end_nodes), 3):
            new_end_id = f"end{i+1}"
            if new_end_id not in existing_end_ids:
                direction_name = sub_directions[i] if i < len(sub_directions) else f"{career_name}专家"
                if direction_name in existing_end_names:
                    direction_name = direction_name + "（资深）"
                nodes.append({
                    "id": new_end_id,
                    "name": direction_name,
                    "type": "end",
                    "description": f"专注于{direction_name}方向的职业发展路径"
                })
    
    if len(middle_nodes) < 3:
        existing_node_ids = set(n['id'] for n in nodes)
        node_num = len(middle_nodes) + 1
        stage_names = ["基础学习", "进阶学习", "实践应用", "高级进阶", "专业深耕"]
        while len(middle_nodes) < 5:
            new_node_id = f"node{node_num}"
            if new_node_id not in existing_node_ids:
                stage_name = stage_names[node_num - 1] if node_num <= len(stage_names) else f"学习阶段{node_num}"
                nodes.append({
                    "id": new_node_id,
                    "name": stage_name,
                    "difficulty": min(5, node_num + 1),
                    "duration": 40 + node_num * 20,
                    "importance": min(5, node_num),
                    "resources": [
                        f"https://search.bilibili.com/all?keyword={career_name}%20{stage_name}",
                        f"https://www.xuetangx.com/search?query={career_name}"
                    ],
                    "description": f"{career_name}学习的{stage_name}阶段"
                })
                middle_nodes = [n for n in nodes if n.get('type') not in ['start', 'end']]
            node_num += 1
    
    start_node = None
    for n in nodes:
        if n.get('type') == 'start':
            start_node = n
            break
    
    if not start_node:
        nodes.insert(0, {"id": "start", "name": "当前起点", "type": "start", "description": "用户当前的知识水平"})
        start_node = nodes[0]
    
    node_id_set = set(n['id'] for n in nodes)
    valid_connections = []
    for conn in connections:
        try:
            if isinstance(conn, dict) and 'from' in conn and 'to' in conn:
                if conn['from'] in node_id_set and conn['to'] in node_id_set and conn['from'] != conn['to']:
                    valid_connections.append(conn)
        except Exception:
            pass
    data['connections'] = valid_connections
    connections = valid_connections
    
    middle_ids = [n['id'] for n in middle_nodes]
    end_ids = [n['id'] for n in end_nodes]
    
    if start_node['id'] not in [c['from'] for c in connections]:
        if middle_ids:
            connections.append({"from": start_node['id'], "to": middle_ids[0], "difficulty": "简单", "duration": "40小时"})
    
    for i in range(len(middle_ids) - 1):
        if middle_ids[i] not in [c['from'] for c in connections if c['to'] == middle_ids[i+1]]:
            connections.append({
                "from": middle_ids[i], 
                "to": middle_ids[i+1], 
                "difficulty": ["简单", "中等", "较难", "困难", "困难"][min(i, 4)],
                "duration": f"{40 + (i+1) * 20}小时"
            })
    
    last_middle = middle_ids[-1] if middle_ids else start_node['id']
    for end_id in end_ids:
        if end_id not in [c['to'] for c in connections]:
            connections.append({
                "from": last_middle,
                "to": end_id,
                "difficulty": "中等",
                "duration": "60小时"
            })
    
    return {"nodes": nodes, "connections": connections}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)