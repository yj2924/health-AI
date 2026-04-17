import streamlit as st
import pandas as pd
import numpy as np
import random
from sklearn.linear_model import LogisticRegression
from datetime import datetime
import requests
import json
from PIL import Image
import io
import base64
import os
from datetime import timedelta

# ========== 页面配置 ==========
st.set_page_config(page_title="身材管理与情绪性进食预警助手", page_icon="🌿", layout="wide")

# ========== 自定义CSS美化 ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e9f0f5 100%);
    }
    .css-1d391kg {
        background-color: #fff8f0;
        border-radius: 20px;
        padding: 10px;
    }
    h1 {
        color: #4a6f5e;
        font-family: 'Helvetica Neue', sans-serif;
        text-align: center;
    }
    .stButton > button {
        background-color: #8fbc8f;
        color: white;
        border-radius: 30px;
        padding: 0.5rem 2rem;
        font-size: 1.2rem;
        border: none;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #6f9e6f;
        transform: scale(1.02);
    }
    .stAlert {
        border-radius: 20px;
        font-size: 1rem;
    }
    .stSlider label {
        font-weight: bold;
        color: #2c4a3e;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌿 你的AI健康伙伴")
# ========== 每日一句正能量 + 成就徽章 ==========
# 1. 随机正能量句子（复用你的话术库，也可以单独定义）
daily_messages = [
    "🌱 每一步都算数，今天也要爱自己。",
    "🌸 你不需要完美，只需要比昨天好一点点。",
    "🍃 压力不是敌人，是你身体在提醒你休息。",
    "🌟 你已经很棒了，今天继续加油！",
    "💧 喝口水，深呼吸，你值得被温柔对待。"
]
# 随机选一句（每次页面刷新都会变）
import random
st.info(random.choice(daily_messages))

# 2. 成就徽章（基于连续使用天数）
# 初始化上次使用日期
if 'last_visit_date' not in st.session_state:
    st.session_state.last_visit_date = None
if 'consecutive_days' not in st.session_state:
    st.session_state.consecutive_days = 0

from datetime import date
today = date.today()
last = st.session_state.last_visit_date

if last is None:
    # 第一次使用
    st.session_state.consecutive_days = 1
    st.session_state.last_visit_date = today
elif last == today:
    # 同一天内重复访问，不增加天数
    pass
elif last == today - timedelta(days=1):
    # 连续第二天
    st.session_state.consecutive_days += 1
    st.session_state.last_visit_date = today
else:
    # 中断了，重置
    st.session_state.consecutive_days = 1
    st.session_state.last_visit_date = today

# 显示徽章
days = st.session_state.consecutive_days
if days >= 30:
    st.sidebar.markdown("🏆 **30天连续使用！健康传奇！** 💪")
elif days >= 7:
    st.sidebar.markdown("🌟 **7天连续使用！自律之星！** ✨")
elif days >= 3:
    st.sidebar.markdown("🏅 **3天连续使用！良好开端！** 🌱")
else:
    st.sidebar.markdown(f"📅 已连续使用 **{days}** 天，坚持就是胜利！")
st.markdown("记录今日状态，获得暴食风险预警和温暖建议")

# ========== 侧边栏输入 ==========
st.sidebar.header("📝 今日数据")
stress = st.sidebar.slider("压力评分 (1-10)", 1, 10, 5)
sleep = st.sidebar.slider("前一晚睡眠小时数", 3.0, 10.0, 7.0, 0.5)
weight = st.sidebar.number_input("当前体重(kg)", 40.0, 150.0, 70.0, 0.1)


# ========== 看板娘：圆滚滚小熊 ==========
st.sidebar.markdown("---")
st.sidebar.markdown("## 🐻 圆滚滚小熊")
st.sidebar.image("mascot.png", width=120, caption="圆滚滚小熊")

# 初始化连续低风险天数
if 'low_risk_streak' not in st.session_state:
    st.session_state.low_risk_streak = 0

# 根据天数决定小熊的“等级”和台词
mascot_icon = "🐻‍❄️"  # 基础图标
mascot_message = "今天也要好好照顾自己哦~ 熊抱一个！"

if st.session_state.low_risk_streak >= 5:
    mascot_icon = "🏆🐻"
    mascot_message = "你已经连续5天低风险了！小熊为你骄傲，给你一个大大的蜂蜜奖章！🍯"
elif st.session_state.low_risk_streak >= 3:
    mascot_icon = "🌟🐻"
    mascot_message = "连续3天状态良好，小熊开心得转圈圈～继续加油！"

st.sidebar.markdown(f"{mascot_icon} **{mascot_message}**")

# ========== 插入位置：侧边栏，小熊图片和台词之后 ==========
if st.sidebar.button("🐻 小熊推荐今天吃什么"):
    if 'food_log' in st.session_state and len(st.session_state.food_log) > 0:
        with st.spinner("小熊正在翻蜂蜜罐找灵感..."):
            # 注意：这里需要传入正确的 user_data，你可以使用之前定义好的 user_data 变量
            rec = get_bear_recommendation(user_data, st.session_state.food_log)
        st.sidebar.success("小熊的建议：")
        st.sidebar.info(rec)
    else:
        st.sidebar.warning("小熊还没看到你的饮食记录呢～先保存一些食物，它就能给你建议啦！")

# ========== 饮食记录本（手动文字版） ==========
with st.sidebar.expander("📝 饮食记录本（手动记录）", expanded=False):
    st.markdown("记录你今天吃了什么（自由描述），小熊会帮你估算热量～")
    
    # 初始化存储
    if 'manual_food_log' not in st.session_state:
        st.session_state.manual_food_log = []  # 每项为 {"text": str, "calories": int, "time": str}
    
    # 输入框
    food_text = st.text_area("食物描述（例如：一碗米饭+炒青菜）", key="manual_food_input")
    
    # 估算热量的简单规则（你可以后续接入 API）
    def estimate_calories_from_text(text):
        # 非常粗略的模拟，实际可调用 LLM 或关键词匹配
        if "米饭" in text:
            return 200
        elif "面" in text:
            return 300
        elif "沙拉" in text:
            return 150
        elif "汉堡" in text:
            return 500
        else:
            return 250  # 默认
    
    if st.button("➕ 记录这一餐"):
        if food_text.strip():
            cal = estimate_calories_from_text(food_text)
            now = datetime.now().strftime("%H:%M")
            st.session_state.manual_food_log.append({
                "text": food_text,
                "calories": cal,
                "time": now
            })
            st.success(f"已记录：{food_text} (约{cal}千卡)")
            # 清空输入框（通过 rerun 重置）
            st.rerun()
        else:
            st.warning("请描述你吃了什么～")
    
    # 显示今日总热量
    if st.session_state.manual_food_log:
        total_cal = sum(item['calories'] for item in st.session_state.manual_food_log)
        st.markdown(f"**今日总摄入：{total_cal} 千卡**")
        
        # 推荐摄入量（基于体重和目标，简单公式）
        # 基础代谢率粗略估算：体重(kg) * 22（女性）或 24（男性），这里取22
        bmr = weight * 22
        if st.session_state.get('health_goal', '健康减脂') == '健康减脂':
            recommended = bmr - 300  # 减脂期缺口
        else:
            recommended = bmr
        st.caption(f"根据你的体重({weight}kg)和健康目标，建议今日总摄入约 {int(recommended)} 千卡。")
        
        # 显示详细列表
        st.markdown("**详细记录：**")
        for item in st.session_state.manual_food_log:
            st.text(f"{item['time']} - {item['text']} ({item['calories']}千卡)")
        
        # 清空按钮（可选）
        if st.button("🗑️ 清空今日记录"):
            st.session_state.manual_food_log = []
            st.rerun()


# ========== 加载/训练模型（模拟数据） ==========
@st.cache_resource
def load_model():
    np.random.seed(42)
    # 生成30天模拟数据
    weights = 70 + np.random.normal(0, 0.5, 30) - np.arange(30) * 0.05
    weights = np.round(weights, 1)
    sleep_hours = np.random.normal(7, 1.5, 30)
    sleep_hours = np.clip(sleep_hours, 3, 10)
    sleep_hours = np.round(sleep_hours, 1)
    stress_vals = np.random.normal(5, 2, 30)
    stress_vals = np.clip(stress_vals, 1, 10)
    stress_vals = np.round(stress_vals).astype(int)
    # 暴食概率与压力正相关、与睡眠负相关
    prob_binge = 1 / (1 + np.exp(-( -3 + 0.5*stress_vals - 0.3*sleep_hours + 0.1*(weights - weights[0]))))
    binge = (np.random.random(30) < prob_binge).astype(int)
    df = pd.DataFrame({
        '压力评分': stress_vals,
        '睡眠小时数': sleep_hours,
        '体重(kg)': weights,
        '是否暴食': binge
    })
    X = df[['压力评分', '睡眠小时数', '体重(kg)']]
    y = df['是否暴食']
    model = LogisticRegression()
    model.fit(X, y)
    return model

model = load_model()

# ========== 本地温暖话术库 ==========
warm_messages = {
    "high": [
        "🌿 感觉到压力了吗？没关系的。试试闭上眼睛，做5次深呼吸，然后喝一杯温水。你不需要用食物来安抚自己，你已经很努力了。",
        "💧 暴食冲动常常是情绪在求救。现在站起来走3分钟，或者给一个朋友发条消息。冲动会在20分钟内消退，你比它强大。",
        "🍵 你不需要完美。今天压力大、睡不好，身体只是想要安慰。给自己泡一杯热茶，抱抱枕头，或者写下来‘我现在感觉……’",
        "🧘 暴食风险较高。请立刻离开当前环境，去洗把脸，听一首你喜欢的歌。你值得被温柔对待，包括被自己温柔对待。"
    ],
    "low": [
        "✨ 今天状态不错！继续保持饮食，记录下此刻的轻松感，它会成为明天的力量。",
        "🌸 你做得很好。今晚记得早点睡，明天醒来会更有掌控感。",
        "🌟 低风险日，可以奖励自己一个非食物的快乐：看一集喜欢的剧、散步听播客。",
        "🌻 像向日葵一样，今天你向着阳光生长。继续保持这份对自己的温柔照顾吧~"
    ]
}

# ========== 主按钮 ==========
if st.button("🚀 获取今日分析"):
    # 构造输入DataFrame（避免特征名警告）
    input_df = pd.DataFrame([[stress, sleep, weight]], 
                            columns=['压力评分', '睡眠小时数', '体重(kg)'])
    risk_prob = model.predict_proba(input_df)[0][1]
    
    st.subheader(f"📊 暴食风险评估：{risk_prob:.1%}")
    
    if risk_prob > 0.7:
        st.warning("⚠️ 检测到高风险")
        advice = random.choice(warm_messages["high"])
    else:
        st.success("✅ 风险较低，继续保持！")
        advice = random.choice(warm_messages["low"])
        # 在 risk_prob 计算之后
    if risk_prob <= 0.7:
        st.session_state.low_risk_streak = st.session_state.get('low_risk_streak', 0) + 1
    else:
        st.session_state.low_risk_streak = 0
    
    st.markdown("### 🤖 AI健康顾问说：")
    st.info(advice)
    
    # 记录历史
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.history.append({
        "时间": now,
        "压力评分": stress,
        "睡眠小时数": sleep,
        "体重(kg)": weight,
        "暴食风险概率": risk_prob
    })

# ========== 拍照识食物 + 个性化AI建议模块 ==========
# 将此模块放在你现有的 app.py 中（历史记录图表之后，“获取今日分析”按钮之前或之后均可）

from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 如果还没有在文件头部导入这些库，请取消注释下面一行
# from datetime import datetime

# 请确保你的API密钥已正确配置
# DEEPSEEK_API_KEY = "你的DeepSeek_API_Key"  # ⚠️ 必须替换成你的真实密钥

# 看板娘角色设定（阶段一先用文本对话，之后可替换为角色形象）
MASCOT_CHARACTER = """你是健康助手中的看板娘“小暖”，一个温暖、可爱、有同理心的健康助手。
    你的特点：
    - 说话温柔，会适当使用颜文字 (｡•ᴗ•｡) 
    - 能理解用户的情绪和健康需求
    - 不会严厉批评，而是用鼓励的方式给出建议
    - 回复简洁友好，控制在80字以内
    - 偶尔会使用🌸 🌟 🍀 等小表情"""

# ==================== 使用 LangChain 进行食物识别 ====================
# 请在文件开头添加以下导入（如果还没有的话）
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage
# import os, json, base64, io
# from PIL import Image

# ========== 使用 LangChain 官方推荐的多模态消息格式 ==========
def analyze_food_image(img_base64):
    """
    使用优化后的提示词调用 DeepSeek 进行食物识别。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        # 请将下面的字符串替换成你自己的真实 API Key
        api_key = "sk-54b5baccd28a40acbc5a94af3488e949"  # ⚠️ 这里已经是你真实的 key，保留即可

    if not api_key:
        return {"error": "未找到API Key，请在代码中设置正确的密钥"}

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import json

    model = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com/v1",
        temperature=0.3,
        max_tokens=500,
    )

    # ========== 关键修改开始 ==========
    # 3. 优化提示词（
    text_prompt = """
你是一位专业的食物识别专家。请仔细观察这张图片，回答以下问题：

1. 图片中是否有食物？如果没有，返回 {"error": "未检测到食物"}。
2. 如果有食物，请识别最显眼的一种食物，并返回：
   - food_name: 具体食物名称（如“香辣炸鸡腿”、“牛肉汉堡”）
   - brand: 可能的品牌或餐厅（如“肯德基”、“麦当劳”、“未知”），根据包装、环境等线索推测
   - reason: 识别依据（如“看到红色包装盒上有KFC标志”或“油炸外皮，有骨头，无面包”）
   - estimated_calories: 估计热量（千卡）
   - nutrition: {protein_g, fat_g, carbs_g}
   - confidence: 你对识别的自信度（0-1之间的小数）

返回格式必须是严格的JSON。
如果无法确定品牌，brand填"未知"。
"""

    content = [
        {"type": "text", "text": text_prompt},
        {"type": "image", "image": {"data": img_base64, "format": "base64"}}
    ]
    
    message = HumanMessage(content=json.dumps(content))
    # ========== 关键修改结束 ==========

    try:
        response = model.invoke([message])
        ai_content = response.content.strip()
        
        # 清理可能的 markdown 标记
        if ai_content.startswith("```json"):
            ai_content = ai_content[7:]
        if ai_content.startswith("```"):
            ai_content = ai_content[3:]
        if ai_content.endswith("```"):
            ai_content = ai_content[:-3]
        ai_content = ai_content.strip()
        
        food_data = json.loads(ai_content)
        return food_data
    except json.JSONDecodeError as json_err:
        return {"error": f"AI返回结果无法解析: {str(json_err)}\n返回内容: {ai_content}"}
    except Exception as e:
        return {"error": f"调用AI服务时出错: {str(e)}"}

def fetch_nutrition_by_name(food_name):
    # 简易数据库（你可以扩展或接入真实API）
    db = {
        "炸鸡腿": {"calories": 250, "protein": 18, "fat": 16, "carbs": 12},
        "香辣鸡翅": {"calories": 320, "protein": 20, "fat": 22, "carbs": 15},
        "香辣鸡腿堡": {"calories": 540, "protein": 28, "fat": 30, "carbs": 45},
        "牛肉汉堡": {"calories": 550, "protein": 25, "fat": 30, "carbs": 45},
        "田园沙拉": {"calories": 150, "protein": 5, "fat": 8, "carbs": 12},
    }
    # 精确匹配
    if food_name in db:
        return db[food_name]
    # 模糊匹配（可选）
    for key in db:
        if key in food_name or food_name in key:
            return db[key]
    return None


# 在 analyze_food_image 函数后面添加
def auto_enrich_with_db(food_data):
    food_name = food_data.get('food_name')
    if not food_name or "error" in food_data:
        return food_data
    try:
        api = openfoodfacts.API(user_agent="YourHealthApp/1.0")
        search = api.product.text_search(food_name, page_size=1)
        if search and search.get('products'):
            product = search['products'][0]
            nut = product.get('nutriments', {})
            db_calories = int(nut.get('energy-kcal_100g', 0))
            if db_calories > 0:  # 有效数据才覆盖
                food_data['estimated_calories'] = db_calories
                food_data['nutrition'] = {
                    'protein_g': int(nut.get('proteins_100g', 0)),
                    'fat_g': int(nut.get('fat_100g', 0)),
                    'carbs_g': int(nut.get('carbohydrates_100g', 0))
                }
                food_data['db_source'] = 'Open Food Facts'
    except Exception as e:
        print(f"自动数据库查询失败: {e}")
    return food_data


def get_personalized_advice(food_info, user_data, user_prefs, brand="未知"):
    url = "https://api.deepseek.com/chat/completions"
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = "sk-54b5baccd28a40acbc5a94af3488e949"  # 你的真实key
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    MASCOT_CHARACTER = "你是健康助手中的看板娘“小暖”，一个温暖、可爱、有同理心的健康助手。说话温柔，会适当使用颜文字，不会严厉批评，而是用鼓励的方式给出建议。回复简洁友好，控制在80字以内，偶尔使用🌸 🌟 🍀 等小表情。"
    
    prompt = f"""
    你是一个温暖的健康助手看板娘，名叫“小暖”。
    用户今天的状态：
    - 压力评分：{user_data.get('stress', '未知')}/10
    - 睡眠时间：{user_data.get('sleep', '未知')} 小时
    - 对甜食的喜爱程度：{user_prefs.get('sweet_tooth', 3)}/5
    - 健康目标：{user_prefs.get('diet_goal', '健康减脂')}
    
    用户正在考虑吃：{food_info.get('food_name', '未知食物')}，来自品牌/餐厅：{brand}。
    预估热量约{food_info.get('estimated_calories', '未知')}千卡。
    
    请你给出个性化的建议：
    1. 是否建议食用（如果用户情绪压力大，可以适度允许一些食物来安抚情绪）
    2. 如果不建议，推荐一个更健康的替代食物（最好来自同一品牌或常见餐厅）
    3. 用温暖可爱的语气回复，80字以内
    
    回复格式：直接说“小暖觉得...”
    """
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": MASCOT_CHARACTER},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"小暖暂时无法回应，请稍后再试~ (错误码：{response.status_code})"
    except Exception as e:
        return f"小暖遇到了一点小状况：{str(e)}，请稍后再试~"


def get_bear_recommendation(user_data, food_log):
    # 整理最近5条记录
    recent = food_log[-5:] if len(food_log) > 5 else food_log
    history_text = "\n".join([f"{item['food_name']} ({item['calories']}千卡, 反馈:{item.get('feedback','无')})" for item in recent])
    
    prompt = f"""
    你是一只圆滚滚的可爱小熊，名叫“圆滚滚”，是用户的健康伙伴。你的性格温暖、憨厚、喜欢鼓励人。
    
    用户今天的状态：
    - 压力评分：{user_data.get('stress', '未知')}/10
    - 睡眠时间：{user_data.get('sleep', '未知')} 小时
    - 健康目标：{user_data.get('goal', '健康减脂')}
    
    用户最近的饮食记录：
    {history_text}
    
    请根据以上信息，推荐1-2种适合用户现在吃的健康食物。要具体说出食物名称，并解释为什么推荐。
    语气要像小熊一样可爱、温暖，可以用一些拟声词（比如“呼噜呼噜”、“熊掌拍拍”），总字数控制在100字以内。
    """
    
    # 复用你已有的 ask_llm 函数（确保 ask_llm 已经定义）
    return ask_llm(prompt)

# ========== 拍照识食物UI模块（终极简单版，永不回退） ==========
import openfoodfacts
from datetime import datetime

st.markdown("---")
st.markdown("## 📸 AI食物识别助手")

col1, col2 = st.columns(2)
with col1:
    picture = st.camera_input("📷 拍照识别食物", key="camera_input")
with col2:
    uploaded_file = st.file_uploader("📁 或从相册上传图片", type=["jpg", "jpeg", "png"], key="file_uploader")

image_file = picture if picture else uploaded_file

# 用于存储当前识别结果和纠正数据的 session_state 变量
if 'ai_food_data' not in st.session_state:
    st.session_state.ai_food_data = None
if 'corrected_name' not in st.session_state:
    st.session_state.corrected_name = ""
if 'corrected_brand' not in st.session_state:
    st.session_state.corrected_brand = ""
if 'nutrition_data' not in st.session_state:
    st.session_state.nutrition_data = None  # 存储查询到的营养数据

# ---------- 1. 图像识别部分 ----------
import openfoodfacts
if image_file:
    image = Image.open(image_file)
    st.image(image, caption="📸 上传的图片", width=300)

    if st.button("🔍 开始分析食物", key="analyze_food_btn"):
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        with st.spinner("小暖正在认真分析你的食物..."):
            food_data = analyze_food_image(img_base64)
            food_data = auto_enrich_with_db(food_data)
        if "error" in food_data:
            st.error(food_data["error"])
        else:
            st.session_state.ai_food_data = food_data
            st.session_state.corrected_name = food_data.get('food_name', '')
            st.session_state.corrected_brand = food_data.get('brand', '未知')
            st.session_state.nutrition_data = None  # 清空旧的查询结果
            st.rerun()  # 刷新页面以显示下面的纠正表单

# ---------- 2. 纠正和查询部分（始终显示，只要 ai_food_data 存在）----------
if st.session_state.ai_food_data is not None:
    st.success(f"✨ AI推测：{st.session_state.ai_food_data.get('food_name', '未知')} (置信度: {st.session_state.ai_food_data.get('confidence', 0):.0%})")
    if st.session_state.ai_food_data.get('brand') and st.session_state.ai_food_data['brand'] != '未知':
        st.caption(f"🔍 推测品牌：{st.session_state.ai_food_data['brand']}")

    st.markdown("### ✏️ 纠正食物信息")
    
    # 使用表单，避免按钮互相干扰
    with st.form(key="correction_form"):
        col1, col2 = st.columns(2)
        with col1:
            name_input = st.text_input("食物名称", value=st.session_state.corrected_name)
        with col2:
            brand_input = st.text_input("品牌/餐厅", value=st.session_state.corrected_brand)
        
        submitted = st.form_submit_button("🔍 查询营养数据")
        if submitted:
            st.session_state.corrected_name = name_input
            st.session_state.corrected_brand = brand_input
            # 调用 Open Food Facts 查询
            try:
                api = openfoodfacts.API(user_agent="YourHealthApp/1.0")
                search = api.product.text_search(name_input, page_size=1)
                if search and search.get('products'):
                    product = search['products'][0]
                    nut = product.get('nutriments', {})
                    st.session_state.nutrition_data = {
                        "calories": int(nut.get('energy-kcal_100g', 0)),
                        "protein": int(nut.get('proteins_100g', 0)),
                        "fat": int(nut.get('fat_100g', 0)),
                        "carbs": int(nut.get('carbohydrates_100g', 0))
                    }
                    st.success(f"已找到 {product.get('product_name', name_input)} 的营养数据")
                else:
                    st.session_state.nutrition_data = None
                    st.warning(f"未找到「{name_input}」的数据，请手动输入")
            except Exception as e:
                st.session_state.nutrition_data = None
                st.error(f"查询失败: {e}")
            st.rerun()

    # 显示营养数据（如果有查询结果则显示，否则显示 AI 原始数据）
    st.markdown("### 📊 营养数据")
    if st.session_state.nutrition_data:
        calories = st.session_state.nutrition_data["calories"]
        protein = st.session_state.nutrition_data["protein"]
        fat = st.session_state.nutrition_data["fat"]
        carbs = st.session_state.nutrition_data["carbs"]
    else:
        # 使用 AI 识别的原始数据
        calories = int(st.session_state.ai_food_data.get('estimated_calories', 0))
        protein = int(st.session_state.ai_food_data.get('nutrition', {}).get('protein_g', 0))
        fat = int(st.session_state.ai_food_data.get('nutrition', {}).get('fat_g', 0))
        carbs = int(st.session_state.ai_food_data.get('nutrition', {}).get('carbs_g', 0))
    
    colA, colB = st.columns(2)
    with colA:
        display_calories = st.number_input("热量（千卡）", value=calories, step=10, key="disp_cal")
        display_fat = st.number_input("脂肪(g)", value=fat, step=1, key="disp_fat")
    with colB:
        display_protein = st.number_input("蛋白质(g)", value=protein, step=1, key="disp_protein")
        display_carbs = st.number_input("碳水(g)", value=carbs, step=1, key="disp_carbs")
    
    # 保存按钮（单独一个按钮，不用表单）
    if st.button("✅ 保存记录"):
        # ========== 插入位置：在保存按钮的 if 内部，构建 corrected_entry 之前 ==========
        feedback = st.radio("小熊想问问：你吃完这个感觉怎么样？", ("很满意😋", "一般🤔", "后悔😞"))
        final_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "food_name": st.session_state.corrected_name,
            "brand": st.session_state.corrected_brand,
            "calories": display_calories,
            "nutrition": {"protein_g": display_protein, "fat_g": display_fat, "carbs_g": display_carbs},
            "ai_original": st.session_state.ai_food_data,
            "feedback": feedback
        }
        if 'food_log' not in st.session_state:
            st.session_state.food_log = []
        st.session_state.food_log.append(final_entry)
        st.success("已保存！小暖记住了~")
        
        # 调用个性化建议
        user_data = {'weight': weight, 'stress': stress, 'sleep': sleep}
        advice = get_personalized_advice(
            {"food_name": final_entry["food_name"], "estimated_calories": final_entry["calories"], "nutrition": final_entry["nutrition"]},
            user_data, st.session_state.user_preferences, final_entry["brand"]
        )
        st.info(advice)
        st.balloons()
        # 可选：清空当前识别状态，开始新一轮
        # st.session_state.ai_food_data = None
        # st.rerun()

# ========== 初始化历史记录会话 ==========
if 'history' not in st.session_state:
    st.session_state.history = []

# ========== 显示历史记录图表 ==========
if len(st.session_state.history) > 0:
    st.markdown("---")
    st.markdown("### 📈 历史记录趋势")
    hist_df = pd.DataFrame(st.session_state.history)
    # 折线图：风险概率变化
    st.line_chart(hist_df.set_index("时间")["暴食风险概率"])
    # 显示最近5条记录表格
    st.dataframe(hist_df.tail(5), use_container_width=True)

#进行拍摄照片识别食物这个部分，吃的什么东西拍一下照片给出精细的反馈：食物的成分和相对应的卡路里，以及探出一个可爱的chatbot（之后会替换成app看板娘之类的可爱角色）告诉你是否建议食用：这个建议是需要完全定制化的，根据每个人不同的饮食习惯，体重，减肥意愿，营养需求，以及心情（情绪坏的时候需要一点甜食等等）来做回答
