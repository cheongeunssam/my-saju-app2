import streamlit as st
import ephem
import datetime
import math
from korean_lunar_calendar import KoreanLunarCalendar

# ==========================================
# 1. 사주 & 2026 전략 엔진 (V35)
# ==========================================
class SajuEngine:
    def __init__(self):
        self.cheon = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        self.ji = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        self.sibsin_names = ['비견', '겁재', '식신', '상관', '편재', '정재', '편관', '정관', '편인', '정인']
        self.unseong_names = ['장생', '목욕', '관대', '건록', '제왕', '쇠', '병', '사', '묘', '절', '태', '양']
        
        self.c_data = [(0,0), (0,1), (1,0), (1,1), (2,0), (2,1), (3,0), (3,1), (4,0), (4,1)]
        self.j_data = [(4,1), (2,1), (0,0), (0,1), (2,0), (1,0), (1,1), (2,1), (3,0), (3,1), (2,0), (4,0)]
        self.unseong_start = [11, 6, 2, 9, 2, 9, 5, 0, 8, 3]

    def _get_ganji(self, gan_idx, ji_idx):
        return f"{self.cheon[gan_idx % 10]}{self.ji[ji_idx % 12]}"

    def _get_sibsin(self, me_idx, target_idx, is_target_cheon=True):
        me_elem, me_pol = self.c_data[me_idx]
        if is_target_cheon: tgt_elem, tgt_pol = self.c_data[target_idx]
        else: tgt_elem, tgt_pol = self.j_data[target_idx]
        rel = (tgt_elem - me_elem + 5) % 5
        is_diff = 0 if me_pol == tgt_pol else 1
        return self.sibsin_names[rel * 2 + is_diff]

    def _get_12unseong(self, day_gan_idx, ji_idx):
        start_ji = self.unseong_start[day_gan_idx]
        is_yang = (day_gan_idx % 2 == 0)
        if is_yang: offset = (ji_idx - start_ji + 12) % 12
        else: offset = (start_ji - ji_idx + 12) % 12
        return self.unseong_names[offset]

    def get_gongmang(self, day_gan, day_ji):
        start_idx = (day_ji - day_gan + 12) % 12
        gm1 = self.ji[(start_idx + 10) % 12]
        gm2 = self.ji[(start_idx + 11) % 12]
        return f"{gm1}{gm2}"

    def get_shinsal(self, day_gan, day_ji, target_ji):
        shinsal_list = []
        groups = {0: 2, 4: 2, 8: 2, 2: 1, 6: 1, 10: 1, 3: 0, 7: 0, 11: 0, 5: 3, 9: 3, 1: 3}
        dohwa_map = {2: 9, 1: 3, 0: 0, 3: 6}
        yeokma_map = {2: 2, 1: 8, 0: 5, 3: 11}
        hwagae_map = {2: 4, 1: 10, 0: 7, 3: 1}
        
        if target_ji == dohwa_map[groups[day_ji]]: shinsal_list.append("도화")
        if target_ji == yeokma_map[groups[day_ji]]: shinsal_list.append("역마")
        if target_ji == hwagae_map[groups[day_ji]]: shinsal_list.append("화개")

        gwin_map = {0: [1, 7], 4: [1, 7], 6: [1, 7], 1: [0, 8], 5: [0, 8], 2: [11, 9], 3: [11, 9], 7: [2, 6], 8: [5, 3], 9: [5, 3]}
        if target_ji in gwin_map[day_gan]: shinsal_list.append("천을귀인")
        
        return ",".join(shinsal_list) if shinsal_list else "-"

    def check_baekho(self, gan, ji):
        baekho = [(0,4), (1,7), (2,10), (3,1), (4,4), (8,10), (9,1)]
        return "백호" if (gan, ji) in baekho else ""
    
    def check_goemigwan(self, gan, ji):
        goe = [(4,10), (6,4), (6,10), (8,4), (8,10), (4,4)]
        return "괴강" if (gan, ji) in goe else ""

    def get_daewoon_data(self, kst_date, direction):
        utc_date = kst_date - datetime.timedelta(hours=9)
        sun = ephem.Sun()
        sun.compute(utc_date)
        start_lon = math.degrees(ephem.Ecliptic(sun).lon)
        start_term_idx = int(start_lon / 15)
        
        check_date = utc_date
        found_date = None
        
        for i in range(1, 1080): 
            check_date += datetime.timedelta(hours=1 * direction)
            sun.compute(check_date)
            curr_lon = math.degrees(ephem.Ecliptic(sun).lon)
            if curr_lon < 0: curr_lon += 360
            curr_term_idx = int(curr_lon / 15)
            if curr_term_idx != start_term_idx:
                found_date = check_date
                break
        
        if not found_date: return 1, "절기 탐색 실패"

        diff_seconds = abs((found_date - utc_date).total_seconds())
        diff_days = diff_seconds / 86400.0
        
        raw_num = diff_days / 3.0
        daewoon_num = int(raw_num)
        remainder = diff_days % 3
        if remainder > 2: daewoon_num += 1
        if daewoon_num < 1: daewoon_num = 1
                     
        return daewoon_num, ""

    # ★ 2026 병오년 전략 리포트 생성기 ★
    def generate_2026_report(self, day_gan_idx, name):
        # 일간 오행 (0:목, 1:화, 2:토, 3:금, 4:수)
        my_elem = self.c_data[day_gan_idx][0]
        
        report = {}
        report['header'] = f"📜 {name}님을 위한 2026 병오년(丙午年) 프리미엄 전략 보고서"
        
        # 일간별 전략 로직
        if my_elem == 0: # 목(Wood) -> 화는 식상(Output)
            report['summary'] = {"keywords": ["#재능폭발", "#탈진주의", "#새로운무대"], "score": 88, "desc": "목화통명(木火通明)의 해입니다. 당신의 능력이 세상에 드러나 빛을 발합니다."}
            report['wealth'] = "아이디어와 기술로 돈을 버는 형국입니다. 투자보다는 본업의 확장에 집중하십시오."
            report['career'] = "승진과 발탁의 운이 강합니다. 두려워말고 앞장서서 리드하는 전략이 유효합니다."
            report['health'] = "지나친 열정으로 인한 '번아웃'을 경계해야 합니다. 심장과 시력 보호에 힘쓰세요."
            report['qimen'] = {"dir": "남쪽(離)", "action": "경문(景門)이 열렸으니 화려하게 치장하고 드러내십시오."}
            report['color'] = "Blue, Black (수 기운으로 열기를 식힘)"
            
        elif my_elem == 1: # 화(Fire) -> 화는 비겁(Rival/Friend)
            report['summary'] = {"keywords": ["#군비쟁재", "#세력확장", "#독단금지"], "score": 75, "desc": "불이 불을 만났으니 기세가 등등합니다. 협력자가 나타나지만 경쟁 또한 치열합니다."}
            report['wealth'] = "돈이 들어오나 나갈 구멍도 큽니다. 동업이나 공동 투자는 신중한 계약이 필요합니다."
            report['career'] = "독단적인 결정은 화를 부릅니다. 팀워크를 활용하되, 성과는 확실히 챙기는 실리 전략이 필요합니다."
            report['health'] = "화기가 너무 강합니다. 혈압, 심혈관 질환에 유의하고 화를 다스리는 명상이 필수입니다."
            report['qimen'] = {"dir": "서북쪽(乾)", "action": "생문(生門)을 찾아 실리를 취하고, 불필요한 자존심 싸움은 피하십시오."}
            report['color'] = "Yellow, Brown (토 기운으로 화기를 설기)"

        elif my_elem == 2: # 토(Earth) -> 화는 인성(Support)
            report['summary'] = {"keywords": ["#문서운", "#귀인도움", "#준비완료"], "score": 92, "desc": "화생토(火生土)의 기운을 받아 든든한 후원자를 얻는 형국입니다."}
            report['wealth'] = "부동산, 문서, 계약과 관련된 이익이 큽니다. 자격증 취득이나 학위 취득에 최적기입니다."
            report['career'] = "윗사람의 인정을 받습니다. 결재권이 강화되고 안정적인 지위를 확보하게 됩니다."
            report['health'] = "너무 편안해서 활동량이 줄어들 수 있습니다. 위장 계통과 비만 관리에 신경 쓰세요."
            report['qimen'] = {"dir": "서쪽(兌)", "action": "개문(開門)의 형국이니, 마음을 열고 윗사람의 제안을 수용하십시오."}
            report['color'] = "White, Gold (금 기운으로 결실을 맺음)"

        elif my_elem == 3: # 금(Metal) -> 화는 관성(Pressure)
            report['summary'] = {"keywords": ["#책임감", "#명예상승", "#스트레스"], "score": 80, "desc": "화극금(火克金). 뜨거운 불이 쇠를 제련하니 명예는 오르나 몸은 고단합니다."}
            report['wealth'] = "돈보다는 명예와 감투를 쓰는 해입니다. 재물 욕심을 내면 화를 입으니 명분을 좇으십시오."
            report['career'] = "승진, 영전의 기회이나 업무 강도가 셉니다. 조직의 압박을 견디면 큰 그릇이 됩니다."
            report['health'] = "폐, 대장, 호흡기 계통이 약해질 수 있습니다. 건조함을 피하고 물을 자주 마시세요."
            report['qimen'] = {"dir": "북쪽(坎)", "action": "휴문(休門)의 지혜가 필요합니다. 나서기보다 물러서서 관조하며 때를 기다리세요."}
            report['color'] = "Black, Navy (수 기운으로 관살을 조절)"

        elif my_elem == 4: # 수(Water) -> 화는 재성(Money)
            report['summary'] = {"keywords": ["#재물성취", "#결과도출", "#에너지소모"], "score": 85, "desc": "수극화(水克火). 내가 불을 끄고 취하는 형국이니 노력한 만큼의 큰 재물을 얻습니다."}
            report['wealth'] = "재물운이 가장 강력합니다. 공격적인 투자와 사업 확장이 유효한 시기입니다."
            report['career'] = "업무 성과가 확실히 드러납니다. 다만 아랫사람 관리나 여자 문제(남성)에 유의하십시오."
            report['health'] = "신장, 방광 등 수 기운이 고갈될 수 있습니다. 충분한 수면과 휴식이 필수 전략입니다."
            report['qimen'] = {"dir": "동쪽(震)", "action": "상문(傷門)을 조심하고, 목표를 향해 직진하되 주변을 살피십시오."}
            report['color'] = "White, Silver (금 기운으로 수원(水源)을 보충)"

        return report

    def calculate(self, year, month, day, hour, minute, gender, name="사용자"):
        try:
            kst_date = datetime.datetime(year, month, day, hour, minute)
        except ValueError: return None

        utc_date = kst_date - datetime.timedelta(hours=9)
        sun = ephem.Sun()
        sun.compute(utc_date, epoch=utc_date) 
        sun_lon = math.degrees(ephem.Ecliptic(sun).lon)
        if sun_lon < 0: sun_lon += 360
        
        target_year = year
        if month == 1: target_year = year - 1
        elif month == 2:
            if sun_lon < 315: target_year = year - 1
        year_gan = (target_year - 4) % 10
        year_ji = (target_year - 4) % 12
        
        temp_lon = sun_lon + 45
        if temp_lon >= 360: temp_lon -= 360
        month_idx = int(temp_lon / 30)
        month_start_map = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0, 5: 2, 6: 4, 7: 6, 8: 8, 9: 0}
        month_gan = (month_start_map[year_gan % 5] + month_idx) % 10
        month_ji = (month_idx + 2) % 12 
        
        base_date = datetime.date(1900, 1, 1)
        target_date_only = datetime.date(year, month, day)
        diff_days = (target_date_only - base_date).days
        day_gan = (diff_days + 10) % 10
        day_ji = (diff_days + 10) % 12 
        
        total_min = hour * 60 + minute
        if total_min >= 23*60 + 30 or total_min < 1*60 + 30:
            time_ji = 0 
            if total_min >= 23*60 + 30: calc_day_gan = (day_gan + 1) % 10
            else: calc_day_gan = day_gan
        else:
            time_ji = ((total_min - 30) // 120 + 1) % 12
            calc_day_gan = day_gan
        time_start_map = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 0, 6: 2, 7: 4, 8: 6, 9: 8}
        time_gan = (time_start_map[calc_day_gan % 5] + time_ji) % 10

        gans = [year_gan, month_gan, day_gan, time_gan]
        jis = [year_ji, month_ji, day_ji, time_ji]
        titles = ["년주", "월주", "일주", "시주"]
        pillars = []
        
        for i in range(4):
            gan_char = self.cheon[gans[i]]
            ji_char = self.ji[jis[i]]
            sibsin = self._get_sibsin(day_gan, gans[i]) if i != 2 else "본원"
            unseong = self._get_12unseong(day_gan, jis[i])
            shinsal = self.get_shinsal(day_gan, day_ji, jis[i])
            sp1 = self.check_baekho(gans[i], jis[i])
            sp2 = self.check_goemigwan(gans[i], jis[i])
            
            pillars.append({
                "title": titles[i], "ganji": f"{gan_char}{ji_char}",
                "sibsin": sibsin, "unseong": unseong,
                "shinsal": shinsal, "special": f"{sp1} {sp2}".strip()
            })

        gongmang = self.get_gongmang(day_gan, day_ji)
        
        is_year_yang = (year_gan % 2 == 0)
        is_man = (gender == '남성')
        
        if (is_man and is_year_yang) or (not is_man and not is_year_yang):
            direction = 1
            dir_text = "순행"
        else:
            direction = -1
            dir_text = "역행"
            
        daewoon_num, debug_msg = self.get_daewoon_data(kst_date, direction)
        
        daewoon_list = []
        for i in range(1, 9):
            d_gan = (month_gan + i * direction) % 10
            d_ji = (month_ji + i * direction) % 12
            age = daewoon_num + (i-1) * 10
            daewoon_list.append(f"**{age}**<br>{self.cheon[d_gan]}{self.ji[d_ji]}")

        # ★ 2026 리포트 생성 ★
        report_2026 = self.generate_2026_report(day_gan, name)

        return {
            "pillars": pillars, 
            "gongmang": gongmang, 
            "daewoon": {"dir": dir_text, "list": daewoon_list, "debug": debug_msg},
            "report_2026": report_2026
        }

# ==========================================
# 2. 스트림릿 UI (V35 - 스크롤 뷰)
# ==========================================
st.set_page_config(page_title="2026 오라클", page_icon="🐎", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .report-box { background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .highlight { color: #d63384; font-weight: bold; }
    .section-title { font-size: 24px; font-weight: bold; margin-top: 30px; margin-bottom: 10px; color: #333; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🐎 2026 병오년(丙午年) 운명 전략가")
st.caption("사주 명식과 2026년의 에너지를 분석하여 최적의 전략을 제시합니다.")
st.markdown("---")

with st.sidebar:
    st.header("📋 사용자 정보 입력")
    name_input = st.text_input("이름", "홍길동")
    b_date = st.date_input("생년월일", datetime.date(1990, 1, 1), min_value=datetime.date(1900,1,1))
    gender = st.radio("성별", ["남성", "여성"])
    b_time = st.time_input("태어난 시간", datetime.time(12, 0))
    cal_type = st.radio("양력/음력", ["양력", "음력(평달)", "음력(윤달)"])
    
    if st.button("운세 분석 시작", type="primary"):
        st.session_state['run'] = True

if 'run' in st.session_state and st.session_state['run']:
    engine = SajuEngine()
    calendar = KoreanLunarCalendar()
    
    year, month, day = b_date.year, b_date.month, b_date.day
    
    if "음력" in cal_type:
        is_leap = "윤달" in cal_type
        calendar.setLunarDate(year, month, day, is_leap)
        year = calendar.solarYear
        month = calendar.solarMonth
        day = calendar.solarDay

    result = engine.calculate(year, month, day, b_time.hour, b_time.minute, gender, name_input)

    if result:
        # 1. 사주 명식표 영역
        st.markdown("<div class='section-title'>1. 사주 원국 (Four Pillars)</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, p in enumerate(reversed(result['pillars'])): 
            idx = 3 - i
            p = result['pillars'][idx]
            with cols[i]:
                st.markdown(f"<div style='text-align:center; padding:10px; border:1px solid #ddd; border-radius:5px;'>"
                            f"<strong>{p['title']}</strong><br>"
                            f"<h2 style='margin:5px 0;'>{p['ganji']}</h2>"
                            f"<span style='color:grey;'>{p['sibsin']}</span><br>"
                            f"<span style='color:blue;'>{p['unseong']}</span>"
                            f"</div>", unsafe_allow_html=True)
                if p['shinsal'] != '-': st.caption(f"✨ {p['shinsal']}")

        # 대운 영역
        st.markdown(f"<div style='margin-top:20px; font-weight:bold;'>🌀 대운 흐름 ({result['daewoon']['dir']})</div>", unsafe_allow_html=True)
        dw_cols = st.columns(8)
        for i, dw in enumerate(result['daewoon']['list']):
            with dw_cols[i]:
                st.markdown(f"<div style='text-align:center; border:1px solid #eee; border-radius:5px; padding:5px; font-size:0.9em;'>"
                            f"{dw}</div>", unsafe_allow_html=True)
        st.info(f"💡 대운수 검증: {result['daewoon']['debug']}")

        # 2. 2026 프리미엄 리포트 영역 (바로 아래에 표시)
        r = result['report_2026']
        st.markdown(f"<div class='section-title'>2. {r['header']}</div>", unsafe_allow_html=True)
        
        # 총평
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.metric("올해의 종합 운세 점수", f"{r['summary']['score']}점")
        with col_b:
            st.markdown("### 🔑 핵심 키워드")
            keywords = " ".join([f"`{k}`" for k in r['summary']['keywords']])
            st.markdown(keywords)
            st.info(r['summary']['desc'])
        
        st.markdown("---")
        
        # 상세 분석
        st.subheader("📊 영역별 정밀 분석")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 💰 재물 전략 (Wealth)")
            st.write(r['wealth'])
            st.markdown("#### 🏥 건강 관리 (Health)")
            st.write(r['health'])
        with c2:
            st.markdown("#### 🏢 직업/사업 (Career)")
            st.write(r['career'])
            st.markdown("#### ❤️ 관계/애정 (Relationship)")
            st.write("새로운 인연보다는 기존 관계를 돈독히 하는 것이 유리합니다. 귀인은 가까운 곳에 있습니다.")

        st.markdown("---")
        
        # 기문둔갑 전략
        st.subheader("🧭 기문둔갑(奇門遁甲) 행동 강령")
        st.markdown(f"""
        <div class='report-box'>
            <p class='big-font'>📍 행운의 방위: <span class='highlight'>{r['qimen']['dir']}</span></p>
            <p><strong>⚔️ 행동 전략:</strong> {r['qimen']['action']}</p>
            <p><strong>🍀 개운 컬러:</strong> {r['color']}</p>
        </div>
        """, unsafe_allow_html=True)
            
    else:
        st.error("분석 중 오류가 발생했습니다.")
else:
    st.info("좌측 사이드바에 정보를 입력하고 '운세 분석 시작'을 눌러주세요.")