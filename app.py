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
    project_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(project_dir, 'poster', 'logo.html')
    with open(logo_path, 'r', encoding='utf-8') as f:
        content = f.read()
    response = app.response_class(content, mimetype='text/html; charset=utf-8')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/app')
def app_page():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(project_dir, 'static', 'index.html')
    with open(index_path, 'r', encoding='utf-8') as f:
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
            "- 推荐的职业应基于用户的专业、特长、爱好、MBTI人格等信息进行**客观分析**，推荐真正适合用户的职业",
            "- 其他推荐职业不必局限于与期望职业相关的领域，可以跨专业推荐用户真正适合的宏观职业方向",
            "- **推荐的职业应是宏观的职业大类，而不是过于细分的职业方向**（例如：推荐\"软件工程师\"而不是\"前端开发工程师\"，推荐\"设计师\"而不是\"UI设计师\"）",
            "- 如果用户专业明确且与某些职业高度相关，可优先推荐相关专业方向；但如果用户的特长、爱好明显指向其他领域，也应客观推荐"
        ]
        
        if desired_career:
            requirement_lines.insert(0, f"- 如果用户填写了期望职业\"{desired_career}\"，**必须**将该期望职业作为推荐结果之一，且放在推荐列表的第一位")
            requirement_lines.insert(1, "- 期望职业的兴趣适配度应根据用户实际匹配情况客观评估，不要人为拔高")
            requirement_lines.insert(2, "- 其他推荐职业不必局限于与期望职业相关的领域")
        
        info_text = '\n'.join(info_lines)
        requirement_text = '\n'.join(requirement_lines)
        user_content = f"""
学生基础信息：
{info_text}

请根据以上信息，为该学生推荐10-12个适合的职业方向。

**重要要求：**
{requirement_text}

对于每个职业，请提供：
1. 职业名称（应为宏观职业大类）
2. 兴趣适配度（0-100的百分比，表示该职业与用户兴趣、特长的匹配程度）
3. 实现难度（0-100的百分比，表示从当前状态到达该职业的难易程度，难度越高百分比越大）
4. 推荐理由（简短说明为什么推荐该职业）
5. 职业介绍（100-150字，介绍该职业的工作内容、发展前景、核心能力要求等）

请使用严格的JSON格式输出，不要包含任何额外文本或Markdown格式。JSON结构如下：
{{
    "careers": [
        {{
            "name": "职业名称",
            "interest_match": 85,
            "difficulty": 60,
            "reason": "简短说明推荐理由",
            "description": "职业介绍（100-150字）"
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
        {"name": "软件工程师", "interest_match": 80, "difficulty": 65, "reason": "适合有编程兴趣和逻辑思维能力的学生", "description": "软件工程师负责设计、开发和维护各类软件系统，涵盖前端、后端、移动端等方向。需要掌握编程语言、数据结构、算法等核心技能，发展前景广阔，薪资水平较高，是数字化时代的核心职业之一。"},
        {"name": "产品经理", "interest_match": 75, "difficulty": 50, "reason": "适合善于沟通、有创意和用户思维的学生", "description": "产品经理负责产品的规划、设计和迭代，需要深入理解用户需求，协调研发、设计、运营等团队推进产品落地。核心能力包括用户调研、需求分析、项目管理和数据驱动决策，发展路径可走向产品总监或VP。"},
        {"name": "设计师", "interest_match": 70, "difficulty": 60, "reason": "适合有艺术天赋和审美能力的学生", "description": "设计师涵盖UI/UX设计、视觉设计、品牌设计等方向，负责产品的视觉呈现和用户体验。需要掌握设计工具、色彩理论、排版布局等技能，注重用户心理和交互逻辑，在互联网、广告、出版等行业需求旺盛。"},
        {"name": "数据分析师", "interest_match": 75, "difficulty": 65, "reason": "适合擅长数学、统计和逻辑分析的学生", "description": "数据分析师通过收集、处理和分析数据，为企业决策提供支持。需要掌握SQL、Python/R、统计学和数据可视化工具，核心工作包括数据清洗、建模分析和报告撰写，在金融、电商、互联网等行业应用广泛。"},
        {"name": "市场营销专员", "interest_match": 65, "difficulty": 45, "reason": "适合善于沟通、有创意和市场敏感度的学生", "description": "市场营销专员负责品牌推广、市场调研、活动策划和渠道运营等工作。需要了解消费者心理、掌握数字营销工具，具备内容创作和数据分析能力，发展方向包括品牌经理、市场总监等。"},
        {"name": "运营专员", "interest_match": 60, "difficulty": 40, "reason": "适合执行力强、善于数据分析的学生", "description": "运营专员负责用户增长、内容运营、活动策划等工作，是连接产品和用户的关键角色。需要具备数据分析、文案写作和活动执行能力，发展方向包括运营经理、运营总监，在互联网行业尤其重要。"},
        {"name": "创业家", "interest_match": 70, "difficulty": 85, "reason": "适合有商业头脑、敢于创新和承担风险的学生", "description": "创业家自主创办企业或项目，需要全面的商业能力，包括市场洞察、团队管理、融资和战略规划。风险高但回报上限大，适合有强烈事业心、抗压能力强的人，成功路径包括连续创业或企业并购退出。"},
        {"name": "教育工作者", "interest_match": 60, "difficulty": 55, "reason": "适合热爱教育、善于表达和有耐心的学生", "description": "教育工作者在学校、培训机构或在线平台从事教学工作，负责课程设计、知识传授和学生培养。需要扎实的专业知识、教学方法和沟通能力，发展方向包括高级教师、教研组长或教育管理者。"},
        {"name": "咨询师", "interest_match": 65, "difficulty": 70, "reason": "适合逻辑清晰、善于分析和沟通的学生", "description": "咨询师为企业提供战略、管理、技术等方面的专业建议，需要强大的分析能力、行业洞察和沟通技巧。工作内容涵盖调研诊断、方案设计和落地实施，在咨询公司或企业内部战略部门发展。"},
        {"name": "内容创作者", "interest_match": 70, "difficulty": 55, "reason": "适合有创作热情和表达能力的学生", "description": "内容创作者在自媒体平台、MCN机构或企业内容团队工作，负责图文、视频、播客等内容策划和制作。需要具备创意策划、文案写作和内容运营能力，变现路径包括广告、知识付费和电商。"},
        {"name": "游戏设计师", "interest_match": 75, "difficulty": 70, "reason": "适合热爱游戏、有创意和技术能力的学生", "description": "游戏设计师负责游戏玩法设计、关卡设计、数值平衡和剧情编排，需要兼顾创意和逻辑。核心技能包括游戏引擎使用、脚本编程和用户体验设计，在游戏行业需求旺盛，薪资待遇优厚。"},
        {"name": "网络安全工程师", "interest_match": 65, "difficulty": 80, "reason": "适合细心、有耐心和技术能力的学生", "description": "网络安全工程师负责保护企业和用户的数字资产安全，工作内容包括漏洞扫描、渗透测试、安全架构设计和应急响应。需要掌握网络协议、密码学、操作系统等底层知识，是高薪且紧缺的职业。"}
    ]
    
    desired_career = basic_info.get('desired_career', '').strip()
    if desired_career:
        existing_index = None
        for i, career in enumerate(default_careers):
            if career['name'] == desired_career:
                existing_index = i
                break
        if existing_index is not None:
            career = default_careers.pop(existing_index)
            default_careers.insert(0, career)
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


def generate_fallback_report(basic_info, deep_answers, career_name=''):
    major_category = basic_info.get('major_category', '')
    major_name = basic_info.get('major_name', '')
    skills = basic_info.get('skills', '')
    hobbies = basic_info.get('hobbies', '')
    mbti = basic_info.get('mbti', '')
    grade = basic_info.get('grade', '')
    desired_career = basic_info.get('desired_career', '')

    target_career = career_name or desired_career or '目标职业'

    q1 = str(deep_answers[0]).strip() if len(deep_answers) > 0 and str(deep_answers[0]).strip() else '未填写'
    q2 = str(deep_answers[1]).strip() if len(deep_answers) > 1 and str(deep_answers[1]).strip() else '未填写'
    q3 = str(deep_answers[2]).strip() if len(deep_answers) > 2 and str(deep_answers[2]).strip() else '未填写'
    q4 = str(deep_answers[3]).strip() if len(deep_answers) > 3 and str(deep_answers[3]).strip() else '未填写'

    report = f"""
## 方向锚点

### 个人画像

| 维度 | 信息 |
|------|------|
| 年级 | {grade} |
| 专业 | {major_name}（{major_category}） |
| 特长 | {skills or '未填写'} |
| 爱好 | {hobbies or '未填写'} |
| MBTI | {mbti or '未填写'} |
| 目标职业 | **{target_career}** |

### 职业方向判定

基于你的专业背景（{major_name}）和个人特质，**{target_career}** 是你的核心发展方向。该方向与你的专业高度匹配，同时能够发挥你的特长和性格优势。

---

## 适配依据

### 专业匹配分析

你的专业「{major_name}」为**{target_career}**提供了以下核心能力支撑：
- 专业知识体系与{target_career}的工作内容高度相关
- 专业课程训练培养了该职业所需的核心思维和能力
- 专业实践经历为职业发展奠定了基础

### 个人特质匹配

"""
    if q1 != '未填写':
        report += f"- **职业价值观**：你提到「{q1[:80]}」，这与{target_career}职业所能提供的价值高度吻合\n"
    if q2 != '未填写':
        report += f"- **抗压能力**：你应对困难的方式是「{q2[:80]}」，这表明你具备该职业所需的韧性\n"
    if q3 != '未填写':
        report += f"- **职业动机**：你选择{target_career}的原因是「{q3[:80]}」，这份内驱力将支撑你长期发展\n"
    if q4 != '未填写':
        report += f"- **自我认知**：你对自身优劣势的分析是「{q4[:80]}」，这种清醒的自我认知是职业发展的重要前提\n"
    if q1 == '未填写' and q2 == '未填写' and q3 == '未填写' and q4 == '未填写':
        report += f"- 建议你认真思考职业价值观和动机，这将帮助你更好地规划{target_career}方向的发展路径\n"

    if mbti:
        mbti_desc = {
            'INTJ': '战略思维型，擅长系统性规划和独立思考', 'INTP': '逻辑分析型，擅长理论研究和问题解决',
            'ENTJ': '领导决策型，擅长组织管理和战略执行', 'ENTP': '创新探索型，擅长创意发想和资源整合',
            'INFJ': '理想主义型，擅长洞察人心和价值驱动', 'INFP': '感性理想型，擅长创意表达和人文关怀',
            'ENFJ': '热情感染型，擅长团队激励和沟通协调', 'ENFP': '热情创意型，擅长人际交往和创意激发',
            'ISTJ': '严谨务实型，擅长执行和细节管理', 'ISFJ': '细致负责型，擅长服务和支持保障',
            'ESTJ': '果断管理型，擅长组织运营和流程管控', 'ESFJ': '热情关怀型，擅长团队协作和客户服务',
            'ISTP': '冷静实操型，擅长技术操作和问题排查', 'ISFP': '温和创意型，擅长审美表达和个性化创作',
            'ESTP': '灵活行动型，擅长应变和现场决策', 'ESFP': '热情表现型，擅长社交互动和氛围营造',
        }
        mbti_text = mbti_desc.get(mbti.upper(), '具备独特的性格优势')
        report += f"\n### MBTI性格分析\n\n你的MBTI类型为**{mbti}**，{mbti_text}。这一性格特质在{target_career}职业中能够发挥独特优势。\n"

    report += f"""

---

## 核心路径

### 你的专属发展路径：{grade} → {target_career}

**阶段一：专业筑基（当前-毕业）**
- 深入学习{major_name}核心课程，GPA保持在3.0以上
- 参与与{target_career}相关的课程项目或竞赛
- 考取该领域的基础证书或资格认证
- 建立行业认知，关注{target_career}领域的最新动态

**阶段二：实践突破（毕业后1-2年）**
- 寻找{target_career}相关的实习或初级岗位
- 在实战中积累项目经验，建立个人作品集
- 拓展行业人脉，参加专业社群和行业活动
- 持续学习行业前沿知识和工具

**阶段三：专业深耕（3-5年）**
- 在{target_career}领域建立专业深度，成为团队核心成员
- 承担更复杂的项目责任，积累管理经验
- 考虑进阶认证或学历提升（如MBA、专业硕士等）
- 开始规划下一步职业跃迁方向

---

## 分阶段行动清单

### 本学期行动

- [ ] 梳理{target_career}所需核心技能清单，对照自身查漏补缺
- [ ] 精读2-3本{target_career}领域经典书籍
- [ ] 关注5个以上行业公众号/博主，建立信息获取渠道
- [ ] 完成至少1个与{target_career}相关的实践项目

### 寒暑假行动

- [ ] 投递{target_career}相关实习岗位，争取实战机会
- [ ] 参加行业峰会或线上论坛，拓展人脉
- [ ] 复盘学习成果，调整下一阶段计划
- [ ] 准备求职材料（简历、作品集等）

### 毕业前行动

- [ ] 完善求职简历，突出与{target_career}的匹配度
- [ ] 模拟面试练习，准备常见面试问题
- [ ] 建立专业作品集或项目展示
- [ ] 投递目标岗位，积极求职

---

## 避坑兜底建议

### 可能遇到的挑战

1. **技能差距**：{target_career}对专业技能要求较高，需持续投入学习
2. **竞争激烈**：该方向求职竞争较大，需提前积累差异化优势
3. **方向迷茫**：实践中可能发现实际工作与预期不符

### 应对策略

1. **建立作品集**：用实际项目证明你的能力，比学历更有说服力
2. **找到导师**：寻找{target_career}领域的前辈指导，少走弯路
3. **保持灵活**：如果主方向受阻，可考虑相关领域作为过渡
4. **持续迭代**：定期复盘职业规划，根据实际情况调整方向

### 备选方案

"""
    sub_directions = get_career_sub_directions(target_career)
    for i, sub in enumerate(sub_directions[:3], 1):
        report += f"{i}. **{sub}** — 作为{target_career}的细分方向，可作为职业发展的备选路径\n"

    report += f"""
---

*本报告基于你的专业背景（{major_name}）、目标职业（{target_career}）及深层探索回答生成。如需更详细的分析，请在网络恢复后重新生成。*
"""
    return report.strip()


@app.route('/api/generate', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        
        basic_info = data.get('basic_info', {})
        deep_answers = data.get('deep_answers', [])
        career_name = data.get('career_name', '').strip()

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

        if career_name:
            info_lines.append(f"- 用户选择的职业方向：{career_name}")

        info_lines.append(f"- MBTI人格：{basic_info.get('mbti', '')}")

        info_text = '\n'.join(info_lines)
        user_content = f"""
学生基础信息：
{info_text}

深层价值观探索回答：
"""
        for i, answer in enumerate(deep_answers, 1):
            user_content += f"- 问题{i}：{str(answer)}\n"

        user_content += f"""

请根据以上信息，围绕用户选择的职业方向「{career_name or desired_career or '未明确'}」，为该学生生成一份专业的学业与职业规划报告。报告需包含以下5个板块：
1. 方向锚点：基于喜欢、擅长、有价值三要素，分析用户选择的方向是否适配，推荐最适配的职业发展方向
2. 适配依据：详细说明推荐方向的匹配理由，结合用户的专业、特长、MBTI和深层回答
3. 核心路径：从当前年级出发，围绕「{career_name or desired_career or '目标职业'}」方向的主要发展路径
4. 分阶段行动清单：按时间周期（学期/学年）规划具体行动步骤
5. 避坑兜底建议：可能遇到的挑战及备选方案

请使用Markdown格式输出，语言温和务实，不制造焦虑。
"""

        result = call_deepseek(DEFAULT_API_KEY, user_content)

        return jsonify({"code": 0, "data": result, "msg": "success"})

    except Exception as e:
        fallback_report = generate_fallback_report(basic_info, deep_answers, career_name)
        return jsonify({"code": 0, "data": fallback_report, "msg": f"生成报告失败，已使用默认报告：{str(e)}"})


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
- 必须形成有向无环图（DAG）结构，父节点指向子节点，禁止循环连接
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
            {"id": "node1", "name": "学习" + career_name + "基础理论与行业认知", "difficulty": 2, "duration": 60, "importance": 5,
             "resources": [{"name": "书籍：专业导论", "url": "https://book.douban.com/subject_search?search_text=专业导论"}],
             "description": "学习" + career_name + "基础理论与行业认知"},
            {"id": "node2", "name": "掌握" + career_name + "核心方法与工具", "difficulty": 3, "duration": 80, "importance": 5,
             "resources": [{"name": "MOOC：专业技能", "url": "https://www.icourse163.org/search.htm?search=专业技能"}],
             "description": "掌握" + career_name + "核心方法与工具"},
            {"id": "node3", "name": "参与" + career_name + "真实项目实践", "difficulty": 4, "duration": 100, "importance": 5,
             "resources": [{"name": "知乎：行业经验", "url": "https://www.zhihu.com/search?type=content&q=行业经验"}],
             "description": "参与" + career_name + "真实项目实践"},
            {"id": "node10", "name": "准备" + career_name + "求职与职业资格", "difficulty": 4, "duration": 60, "importance": 5,
             "resources": [{"name": "B站：职业资格考试", "url": "https://search.bilibili.com/all?keyword=职业资格考试"}],
             "description": "准备" + career_name + "求职材料与职业资格认证"}
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

    ensure_learning_resources(nodes, career_name)

    return {
        "nodes": nodes,
        "connections": connections
    }


def ensure_learning_resources(nodes, career_name):
    """确保每个学习节点至少包含3个资源，其中至少2个是B站视频。"""
    bilibili_templates = [
        ("B站：{name}基础入门教程", "https://search.bilibili.com/all?keyword={name}%20基础入门教程"),
        ("B站：{name}实战项目教程", "https://search.bilibili.com/all?keyword={name}%20实战项目教程"),
        ("B站：{name}进阶技巧", "https://search.bilibili.com/all?keyword={name}%20进阶技巧"),
        ("B站：{name}面试求职经验", "https://search.bilibili.com/all?keyword={name}%20面试求职经验"),
    ]
    other_templates = [
        ("MOOC：{name}专业课程", "https://www.icourse163.org/search.htm?search={name}"),
        ("知乎：{name}学习路线", "https://www.zhihu.com/search?type=content&q={name}%20学习路线"),
        ("书籍：{name}入门到精通", "https://book.douban.com/subject_search?search_text={name}%20入门到精通"),
    ]

    for node in nodes:
        if node.get('type') in ('start', 'end', 'branch'):
            continue
        resources = node.get('resources') or []
        if not isinstance(resources, list):
            resources = []
        existing_urls = {r.get('url') for r in resources if isinstance(r, dict) and r.get('url')}

        def add_resource(name_tmpl, url_tmpl):
            url = url_tmpl.replace('{name}', career_name)
            if url in existing_urls:
                return False
            existing_urls.add(url)
            resources.append({
                "name": name_tmpl.replace('{name}', career_name),
                "url": url
            })
            return True

        # 先补齐B站视频到至少2个
        bilibili_count = sum(1 for r in resources if isinstance(r, dict) and 'bilibili.com' in (r.get('url') or ''))
        for name_tmpl, url_tmpl in bilibili_templates:
            if bilibili_count >= 2:
                break
            if add_resource(name_tmpl, url_tmpl):
                bilibili_count += 1

        # 再补齐总数到至少3个
        idx = 0
        while len(resources) < 3:
            name_tmpl, url_tmpl = other_templates[idx % len(other_templates)]
            add_resource(name_tmpl, url_tmpl)
            idx += 1

        node['resources'] = resources

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
        stage_templates = [
            ("学习{name}基础理论与核心概念", "掌握{name}入门知识，建立基础认知框架"),
            ("掌握{name}核心方法与工具", "学习{name}常用方法论和工具操作"),
            ("参与{name}真实项目实战", "通过实际项目提升{name}应用能力"),
            ("深入研究{name}进阶技术与案例", "学习{name}高级技能与行业最佳实践"),
            ("构建{name}领域综合解决方案", "整合所学知识，形成{name}系统性能力")
        ]
        while len(middle_nodes) < 5:
            new_node_id = f"node{node_num}"
            if new_node_id not in existing_node_ids:
                stage_name, stage_desc = stage_templates[node_num - 1] if node_num <= len(stage_templates) else (
                    f"{career_name}学习阶段{node_num}",
                    f"{career_name}学习阶段{node_num}的专项内容"
                )
                stage_name = stage_name.replace('{name}', career_name)
                stage_desc = stage_desc.replace('{name}', career_name)
                nodes.append({
                    "id": new_node_id,
                    "name": stage_name,
                    "difficulty": min(5, node_num + 1),
                    "duration": 40 + node_num * 20,
                    "importance": min(5, node_num),
                    "resources": [
                        {"name": f"B站：{career_name}基础入门教程", "url": f"https://search.bilibili.com/all?keyword={career_name}%20基础入门教程"},
                        {"name": f"B站：{career_name}实战项目教程", "url": f"https://search.bilibili.com/all?keyword={career_name}%20实战项目"},
                        {"name": f"MOOC：{career_name}专业课程", "url": f"https://www.icourse163.org/search.htm?search={career_name}"}
                    ],
                    "description": stage_desc
                })
                existing_node_ids.add(new_node_id)
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