import streamlit as st
import pandas as pd
import numpy as np
import random
from sklearn.linear_model import LogisticRegression
from datetime import datetime

# ========== 页面配置 ==========
st.set_page_config(page_title="身材管理与暴食预警助手", page_icon="🌿", layout="wide")

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
st.markdown("记录今日状态，获得暴食风险预警和温暖建议")

# ========== 侧边栏输入 ==========
st.sidebar.header("📝 今日数据")
stress = st.sidebar.slider("压力评分 (1-10)", 1, 10, 5)
sleep = st.sidebar.slider("前一晚睡眠小时数", 3.0, 10.0, 7.0, 0.5)
weight = st.sidebar.number_input("当前体重(kg)", 40.0, 150.0, 70.0, 0.1)

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
        "✨ 今天状态不错！继续保持正念饮食，记录下此刻的轻松感，它会成为明天的力量。",
        "🌸 你做得很好。今晚记得早点睡，明天醒来会更有掌控感。",
        "🌟 低风险日，可以奖励自己一个非食物的快乐：看一集喜欢的剧、散步听播客。",
        "🌻 像向日葵一样，今天你向着阳光生长。继续保持这份对自己的温柔照顾吧~"
    ]
}

# ========== 初始化历史记录会话 ==========
if 'history' not in st.session_state:
    st.session_state.history = []

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

# ========== 显示历史记录图表 ==========
if len(st.session_state.history) > 0:
    st.markdown("---")
    st.markdown("### 📈 历史记录趋势")
    hist_df = pd.DataFrame(st.session_state.history)
    # 折线图：风险概率变化
    st.line_chart(hist_df.set_index("时间")["暴食风险概率"])
    # 显示最近5条记录表格
    st.dataframe(hist_df.tail(5), use_container_width=True)