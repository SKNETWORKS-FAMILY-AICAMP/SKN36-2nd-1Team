"""KKeeper ③ 실험 관리 — 실험군·대조군 A/B 테스트 설계, 결과 입력, 판정 (주소: /experiments).

- 결과는 기본적으로 '실제 캠페인 결과'를 입력해요 (숫자 직접 입력 또는 CSV 업로드).
- '시연 모드'를 켜면 이탈 모델로 만든 가상 결과를 채워 줘요. 이때 판정과 라이브러리 카드에
  항상 '시뮬레이션' 표시가 붙어요.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common import db  # noqa: E402
from common.constants import CHANNELS, DEFAULT_METRIC, VERDICT_KIND, seg_display  # noqa: E402
from common.data import apply_conditions, load_assets  # noqa: E402
from common.experiment import (WHATIF_LEVERS, balance_table, decide_verdict, simulate_ab,  # noqa: E402
                               split_ab, two_prop_test)

st.set_page_config(page_title="실험 관리 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("experiments")
ss = st.session_state


# ─────────────────────────────────────────────
# 공통 조각
# ─────────────────────────────────────────────
def sec_head(num: str, title: str, right: str = "") -> None:
    ui.html(f'<div class="kk kk-sechead"><div><span class="kk-secnum">{num}</span><span class="kk-sectitle">{title}</span></div>{right}</div>')


def group_card(title: str, sub: str, group: pd.DataFrame, accent: bool) -> str:
    border = f"border-color:{T['accent_line']};" if accent else ""
    tag = ui.badge("전략 적용", "accent") if accent else ui.badge("아무것도 안 함", "neutral")
    expected = group["churn_prob"].sum()
    return (f'<div class="kk kk-card" style="padding:18px 20px; {border}"><div style="display:flex; justify-content:space-between; align-items:center">'
            f'<span style="font-size:16px; font-weight:700">{title}</span>{tag}</div><div class="kk-cap" style="margin-top:2px">{sub}</div>'
            f'<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:14px">'
            f'{ui.kpi("고객 수", f"{len(group):,}명")}{ui.kpi("평균 이탈확률", ui.pct(group["churn_prob"].mean()))}'
            f'{ui.kpi("예상 이탈자", f"{expected:,.1f}명")}</div></div>')


def csv_bytes(ids, group_name: str) -> bytes:
    return pd.DataFrame({"msno": list(ids), "group": group_name}).to_csv(index=False).encode("utf-8-sig")


def balance_html(table: pd.DataFrame) -> str:
    rows = []
    for _, r in table.iterrows():
        ok = abs(r["표준화 차이"]) < 0.1
        rows.append([r["지표"], f'{r["그룹 A"]:,.3f}', f'{r["그룹 B"]:,.3f}', f'{r["표준화 차이"]:+.3f}',
                     ui.badge("비슷함", "good") if ok else ui.badge("차이 있음", "warn")])
    return ui.table(["지표", "실험군", "대조군", "표준화 차이", ""], rows, right={1, 2, 3})


def verdict_card(test: dict, verdict: str, reason: str, simulated: bool, exp: dict) -> str:
    kind = VERDICT_KIND.get(verdict, "accent")
    sim = ui.badge("시뮬레이션", "warn") if simulated else ""
    top = max(test["p_t"], test["p_c"], 1e-9)
    hyp = ""
    if exp.get("hyp_p_ctrl") is not None and exp.get("hyp_p_treat") is not None:
        hyp = (f'<div class="kk-cap">가설(모델): {(exp["hyp_p_ctrl"] - exp["hyp_p_treat"]) * 100:.2f}%p 감소 예상 → '
               f'실측: {test["diff"] * 100:+.2f}%p</div>')

    def bar(label, p, x, n, color):
        return (f'<div style="display:grid; grid-template-columns:70px 1fr 150px; align-items:center; gap:12px; font-size:14px">'
                f'<span>{label}</span>{ui.track(p / top, color, 14)}<span class="kk-num-font" style="text-align:right">'
                f'{p * 100:.2f}% <span class="kk-cap">({x:,}/{n:,})</span></span></div>')
    return f"""<div class="kk kk-card" style="display:flex; flex-direction:column; gap:14px; border-color:{T['accent_line']}">
<div style="display:flex; justify-content:space-between; align-items:center"><span style="font-size:15px; font-weight:700">판정</span>
<span style="display:flex; gap:6px">{ui.badge(verdict, kind)}{sim}</span></div>
{bar("실험군", test["p_t"], test["x_t"], test["n_t"], T["accent"])}
{bar("대조군", test["p_c"], test["x_c"], test["n_c"], T["strong_border"])}
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px">
{ui.kpi("이탈률 차이 (대조군−실험군)", f'{test["diff"] * 100:+.2f}%p')}
{ui.kpi("95% 신뢰구간", f'{test["ci_low"] * 100:+.2f} ~ {test["ci_high"] * 100:+.2f}%p')}
{ui.kpi("p-value", ui.pval(test["p_value"]))}</div>
<div style="font-size:13px; color:{T['text2']}">{ui.esc(reason)}</div>{hyp}</div>"""


def lever_text(levers: dict) -> str:
    return ", ".join(f'{WHATIF_LEVERS[k]["label"]} {v}%' for k, v in levers.items() if v and k in WHATIF_LEVERS) or "-"


# ─────────────────────────────────────────────
# 1) 새 실험 설계
# ─────────────────────────────────────────────
def design_view(strategy: dict, match: dict) -> None:
    try:
        assets = load_assets()
    except FileNotFoundError as error:
        ui.show_missing_files(error)
        return
    segment = match["segment"]
    matched, _ = apply_conditions(assets["risk"], strategy)
    target = matched[matched["segment"] == segment]
    if len(target) < 2:
        st.warning("실험 대상이 2명 미만이어서 그룹을 분할할 수 없습니다. 고객 매칭에서 다른 유형을 선택하십시오.")
        return

    seed = ss.setdefault("design_seed", 42)
    key = (segment, match.get("conditions"), seed, len(target))
    if ss.get("design", {}).get("key") != key:
        treat, ctrl = split_ab(target, seed=seed)
        ss["design"] = {"key": key, "treat": treat.index.tolist(), "ctrl": ctrl.index.tolist()}
    treat = target.loc[ss["design"]["treat"]]
    ctrl = target.loc[ss["design"]["ctrl"]]

    ui.html(
        ui.page_title(
            "A/B 테스트 설계",
            f"{seg_display(segment)} {len(target):,}명 대상 실험군·대조군 배정하기",
            "3단계 · 실험 관리"
        )
    )

    with st.container(key="kkbox-design"):
        sec_head("01", "실험 설계")
        c1, c2 = st.columns(2)
        with c1:
            ui.html(group_card("실험군", "캠페인 적용 대상", treat, True))
            st.download_button("실험군 명단 CSV", csv_bytes(treat["msno"], "실험군"), "treatment_group.csv", "text/csv",
                               key="dl-t", **ui.WIDE)
        with c2:
            ui.html(group_card("대조군", "캠페인 미적용 대상", ctrl, False))
            st.download_button("대조군 명단 CSV", csv_bytes(ctrl["msno"], "대조군"), "control_group.csv", "text/csv",
                               key="dl-c", **ui.WIDE)

        b1, b2 = st.columns([1.4, 1])
        with b1:
            table = balance_table(treat, ctrl)
            balanced = bool((table["표준화 차이"].abs() < 0.1).all()) if len(table) else True
            ui.html(f'<div class="kk"><div class="kk-card-title">두 그룹 균형 확인 {ui.badge("균형 양호", "good") if balanced else ui.badge("차이 있음", "warn")}</div>'
                    f'<div class="kk-card-note">표준화 차이의 절댓값이 0.1 미만이면 두 그룹이 유사한 것으로 판단합니다.</div></div>')
            ui.html(f'<div class="kk">{balance_html(table)}</div>')
            if st.button("다른 조합으로 다시 나누기", key="resplit"):
                ss["design_seed"] = seed + 1
                st.rerun()
        with b2:
            need = match.get("required_n")
            per_group = min(len(treat), len(ctrl))
            if need:
                share = min(per_group / need, 1.0)
                status = (ui.badge("충분", "good") if per_group >= need else ui.badge("부족", "warn"))
                need_text = f"그룹당 필요 {need:,}명 · 현재 {per_group:,}명"
            else:
                share, status, need_text = 0, ui.badge("계산 불가", "neutral"), "모델의 예상 차이가 없어 필요 인원을 계산할 수 없습니다."
            ui.html(f"""<div class="kk" style="display:flex; flex-direction:column; gap:12px">
<div class="kk-card-title">표본 수 충족 여부 {status}</div>
<div class="kk-card-note">가설 수준의 차이를 검출하기 위한 인원 (유의수준 5%, 검정력 80%)</div>
{ui.track(share, T['good_text'] if share >= 1 else T['warn_text'], 10)}
<div class="kk-cap">{need_text}</div>
<div class="kk-tip"><b>실험 전 가설</b> · 대조군 예상 이탈률 {ui.pct(match['p_ctrl'], 2)} → 실험군 {ui.pct(match['p_treat'], 2)}<br>
<span style="font-size:12px">이탈 모델의 예측값이며, 최종 판정은 실제 결과를 기준으로 합니다.</span></div></div>""")

    # 실험 설계와 캠페인 실행 설정 사이 여백
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    with st.container(key="kkbox-campaign"):
        sec_head("02", "캠페인 실행 설정")
        c1, c2 = st.columns([1.6, 1])
        with c1:
            title = st.text_input("실험 이름", value=strategy.get("name") or "새 실험", key="d_title", max_chars=120)
        with c2:
            channel_options = strategy.get("channels") or CHANNELS
            channel = st.selectbox("전달 채널", channel_options, key="d_channel")
        c3, c4, c5 = st.columns(3)
        with c3:
            start = st.date_input("시작일", value=date.today(), key="d_start")
        with c4:
            end = st.date_input("종료일", value=date.today() + timedelta(days=14), key="d_end")
        with c5:
            metric = st.text_input("판단 기준", value=DEFAULT_METRIC, key="d_metric")
        ui.html(f'<div class="kk kk-cap">전략 · {ui.esc(strategy.get("kind", ""))} · {ui.esc(strategy.get("goal", ""))} '
                f'· 행동 목표(가정) {ui.esc(lever_text(strategy.get("levers", {})))}</div>')

    # 캠페인 실행 설정과 하단 버튼 박스 사이 여백
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    with st.container(key="kkfoot-design"):
        msg = st.empty()
        f1, _, f2 = st.columns([1, 2.5, 1.4], vertical_alignment="center")
        with f1:
            if st.button("← 고객 매칭", key="back-match"):
                st.switch_page(ui.PAGE_FILES["matching"])
        with f2:
            if st.button("실험 시작하기 (저장)", type="primary", key="start-exp", **ui.WIDE):
                if end < start:
                    msg.error("종료일은 시작일보다 빠를 수 없습니다.")
                    return
                payload = {
                    "title": title.strip() or "새 실험",
                    "strategy_kind": strategy.get("kind"), "strategy_goal": strategy.get("goal"),
                    "strategy_desc": strategy.get("desc"),
                    "conditions": {"period": strategy.get("period"), "last": strategy.get("last"), "plans": strategy.get("plans")},
                    "levers": strategy.get("levers", {}),
                    "segment": segment, "hyp_p_ctrl": float(match["p_ctrl"]), "hyp_p_treat": float(match["p_treat"]),
                    "hyp_reduced": float(match["reduced"]), "required_n": match.get("required_n"),
                    "channel": channel, "start_date": start, "end_date": end, "metric": metric, "seed": int(seed),
                    "n_treat": len(treat), "n_ctrl": len(ctrl), "status": "진행 중",
                }
                try:
                    exp_id = db.create_experiment(payload, treat["msno"], ctrl["msno"])
                except Exception as error:
                    msg.error(f"저장할 수 없습니다: {error}")
                    return
                ss["open_exp"] = exp_id
                ss["exp_view"] = "results"
                ss.pop("match", None)
                ss.pop("design", None)
                ss["_toast"] = "실험이 저장되었습니다. 캠페인 종료 후 결과를 입력하십시오."
                st.rerun()


# ─────────────────────────────────────────────
# 2) 실험 목록 · 결과 입력 · 판정
# ─────────────────────────────────────────────
def exp_label(e: dict, display_no: int) -> str:
    state = e.get("verdict") or ("결과 입력 대기" if db.is_waiting(e) else e["status"])
    return f"#{display_no} · {e['title']} · {state}"


def counts_from_csv(file, members: pd.DataFrame) -> dict | None:
    """업로드한 CSV(msno, is_churn)를 배정 명단과 맞춰 그룹별 인원·이탈자를 세요."""
    if hasattr(file, "seek"):
        file.seek(0)
    try:
        df = pd.read_csv(file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        st.error("CSV 파일을 읽을 수 없습니다. 쉼표로 구분된 msno, is_churn 컬럼을 확인하십시오.")
        return None
    cols = {c.lower(): c for c in df.columns}
    if "msno" not in cols or "is_churn" not in cols:
        st.error("CSV에 msno, is_churn 컬럼이 필요합니다.")
        return None
    df = df.rename(columns={cols["msno"]: "msno", cols["is_churn"]: "is_churn"})
    df["msno"] = df["msno"].astype(str)
    df["is_churn"] = pd.to_numeric(df["is_churn"], errors="coerce").fillna(0).astype(int).clip(0, 1)
    joined = members.merge(df[["msno", "is_churn"]].drop_duplicates("msno"), on="msno", how="inner")
    if joined.empty:
        st.error("업로드한 명단과 실험 배정 명단에 일치하는 회원이 없습니다.")
        return None
    t, c = joined[joined["grp"] == "T"], joined[joined["grp"] == "C"]
    missing = len(members) - len(joined)
    if missing:
        st.info(f"배정 명단 중 결과 파일에 없는 {missing:,}명을 제외했습니다.")
    return {"n_t": len(t), "x_t": int(t["is_churn"].sum()), "n_c": len(c), "x_c": int(c["is_churn"].sum())}


@st.cache_data(show_spinner="이탈 모델 기반 가상 결과 생성 중…")
def simulated_counts(exp_id: int, seed: int, levers: tuple) -> dict:
    members = db.get_members(exp_id)
    kk = load_assets()["kk"].copy()
    kk["msno"] = kk["msno"].astype(str)
    kk = kk.set_index("msno")
    treat = kk.loc[kk.index.intersection(members.loc[members["grp"] == "T", "msno"])].reset_index()
    ctrl = kk.loc[kk.index.intersection(members.loc[members["grp"] == "C", "msno"])].reset_index()
    return simulate_ab(treat, ctrl, dict(levers), load_assets()["bundle"], seed=seed)


def result_view() -> None:
    try:
        exps = db.list_experiments()
    except Exception as error:
        st.error(f"실험 저장소에 연결할 수 없습니다: {error}")
        return
    if not exps:
        ui.html(ui.page_title("실험 관리", "등록된 실험이 없습니다."))
        ui.html(f'<div class="kk kk-card" style="border-style:dashed; color:{T["muted"]}; padding:40px">'
                '마케팅 방안 입력 및 고객 매칭 완료 후 A/B 테스트를 설계할 수 있습니다.</div>')
        # 안내 박스와 이동 버튼 사이 간격
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        if st.button("마케팅 설계로 가기 →", type="primary", key="go-plan"):
            st.switch_page(ui.PAGE_FILES["marketing"])
        return

    ids = [e["id"] for e in exps]
    request = ss.pop("open_exp", None)             # 현황·라이브러리·설계 화면에서 넘겨준 실험
    if request in ids:
        ss["exp_pick"] = request
    if ss.get("exp_pick") not in ids:
        ss["exp_pick"] = ids[0]
    # DB의 실제 id는 유지하고, 화면에는 현재 목록 기준 연속 번호를 표시
    display_no_by_id = {e["id"]: i for i, e in enumerate(sorted(exps, key=lambda x: x["id"]), start=1)}
    labels = {e["id"]: exp_label(e, display_no_by_id[e["id"]]) for e in exps}
    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
    exp_id = st.selectbox("실험 고르기", ids, format_func=lambda i: labels[i], key="exp_pick", label_visibility="collapsed")
    exp = db.get_experiment(exp_id)
    display_no = display_no_by_id.get(exp_id, exp_id)
    state = exp.get("verdict") or ("결과 입력 대기" if db.is_waiting(exp) else exp["status"])
    ui.html(ui.context_html({"name": exp["title"], "kind": exp.get("strategy_kind") or ""}, seg_display(exp["segment"]),
                            f"#{display_no} · {state}"))

    state_badge = (ui.badge(exp["verdict"], VERDICT_KIND.get(exp["verdict"], "accent")) if exp.get("verdict")
                   else ui.badge("결과 입력 대기", "warn") if db.is_waiting(exp) else ui.badge("진행 중", "accent"))
    sim_badge = ui.badge("시뮬레이션", "warn") if exp.get("is_simulated") else ""
    ui.html(f'<div class="kk" style="display:flex; align-items:center; gap:10px; flex-wrap:wrap">'
            f'<h1 class="kk-title">{ui.esc(exp["title"])}</h1>{state_badge}{sim_badge}</div>')
    # 실험명과 캠페인 실행 박스 사이 여백
    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    # 02 캠페인 요약
    with st.container(key="kkbox-summary"):
        sec_head("02", "캠페인 실행", ui.badge(f'{exp.get("start_date") or "-"} ~ {exp.get("end_date") or "-"}', "neutral"))
        ui.html(f"""<div class="kk" style="display:grid; grid-template-columns:repeat(4,1fr); gap:14px">
{ui.kpi("대상 유형", seg_display(exp["segment"]))}
{ui.kpi("실험군 / 대조군", f'{int(exp.get("n_treat") or 0):,} / {int(exp.get("n_ctrl") or 0):,}명')}
{ui.kpi("전달 채널", ui.esc(exp.get("channel") or "-"))}
{ui.kpi("가설 (모델)", f'{ui.pct(exp.get("hyp_p_ctrl"), 2)} → {ui.pct(exp.get("hyp_p_treat"), 2)}')}</div>
<div class="kk kk-cap" style="margin-top:6px">판단 기준 · {ui.esc(exp.get("metric") or "-")} · 전략 {ui.esc(exp.get("strategy_kind") or "-")} · {ui.esc(exp.get("strategy_goal") or "-")} · 행동 목표(가정) {ui.esc(lever_text(exp.get("levers") or {}))}</div>""")
        members = db.get_members(exp_id)
        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button("실험군 명단 CSV", csv_bytes(members.loc[members["grp"] == "T", "msno"], "실험군"),
                           f"exp{exp_id}_treatment.csv", "text/csv", key=f"dlt-{exp_id}", **ui.WIDE)
        d2.download_button("대조군 명단 CSV", csv_bytes(members.loc[members["grp"] == "C", "msno"], "대조군"),
                           f"exp{exp_id}_control.csv", "text/csv", key=f"dlc-{exp_id}", **ui.WIDE)

    # 캠페인 실행 박스와 결과 입력 박스 사이 여백
    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)

    # 03 결과 입력과 판정
    with st.container(key="kkbox-result"):
        demo = st.toggle("시연 모드 · 이탈 모델로 만든 가상 결과 채우기", key=f"demo-{exp_id}", value=bool(exp.get("is_simulated")))
        sec_head("03", "결과 입력과 판정")
        counts = None
        if demo:
            ui.html('<div class="kk kk-warnbox"><b>시연 모드</b> 아래 결과는 실제 캠페인 결과가 아닌 이탈 모델 기반 가상 값입니다. '
                    '판정 및 라이브러리 카드에 ‘시뮬레이션’ 표시가 적용됩니다.</div>')
            try:
                counts = simulated_counts(exp_id, int(exp.get("seed") or 42), tuple(sorted((exp.get("levers") or {}).items())))
            except FileNotFoundError as error:
                ui.show_missing_files(error)
            if counts:
                t_txt = f"{counts['x_t']:,} / {counts['n_t']:,}명"
                c_txt = f"{counts['x_c']:,} / {counts['n_c']:,}명"
                ui.html(f'<div class="kk" style="display:grid; grid-template-columns:repeat(2,1fr); gap:14px">'
                        f'{ui.kpi("실험군 이탈자 (가상)", t_txt)}{ui.kpi("대조군 이탈자 (가상)", c_txt)}</div>')
        else:
            how = st.radio("입력 방법", ["숫자 직접 입력", "결과 CSV 올리기 (msno, is_churn)"], horizontal=True, key=f"how-{exp_id}")
            if how.startswith("숫자"):
                prev = exp if exp.get("obs_n_treat") and not exp.get("is_simulated") else {}
                c1, c2, c3, c4 = st.columns(4)
                n_t = c1.number_input("실험군 인원", min_value=0, step=1, key=f"nt-{exp_id}",
                                      value=int(prev.get("obs_n_treat") or exp.get("n_treat") or 0))
                x_t = c2.number_input("실험군 이탈자 수", min_value=0, step=1, key=f"xt-{exp_id}", value=int(prev.get("obs_x_treat") or 0))
                n_c = c3.number_input("대조군 인원", min_value=0, step=1, key=f"nc-{exp_id}",
                                      value=int(prev.get("obs_n_ctrl") or exp.get("n_ctrl") or 0))
                x_c = c4.number_input("대조군 이탈자 수", min_value=0, step=1, key=f"xc-{exp_id}", value=int(prev.get("obs_x_ctrl") or 0))
                if x_t or x_c:
                    counts = {"n_t": n_t, "x_t": x_t, "n_c": n_c, "x_c": x_c}
            else:
                file = st.file_uploader("캠페인 종료 후 결과 파일", type=["csv"], key=f"up-{exp_id}")
                if file is not None:
                    counts = counts_from_csv(file, members)

        test = verdict = None
        if counts:
            try:
                test = two_prop_test(counts["n_t"], counts["x_t"], counts["n_c"], counts["x_c"])
                verdict, reason = decide_verdict(test, exp.get("required_n"))
                ui.html(verdict_card(test, verdict, reason, demo, exp))
            except ValueError as error:
                st.error(str(error))
                test = None
        else:
            ui.html(f'<div class="kk kk-card" style="border-style:dashed; text-align:center; color:{T["muted"]}; padding:32px">'
                    '결과 입력 후 판정이 제공됩니다.<br><span class="kk-cap">실험군·대조군의 실제 이탈자 수를 입력하거나 결과 CSV를 업로드하십시오.</span></div>')

        note = st.text_area("메모 (선택)", value=exp.get("note") or "", key=f"note-{exp_id}", height=70)

    # 하단 작업 버튼: 동일한 너비와 높이, 판정 저장을 맨 오른쪽에 배치
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown(f"""
    <style>
    .st-key-kk-result-actions [data-testid="stButton"] button,
    .st-key-kk-result-actions [data-testid="stPopover"] button {{
        width: 100% !important;
        min-height: 48px !important;
        height: 48px !important;
        border-radius: 999px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }}
    .st-key-kk-result-actions [data-testid="stPopover"] button {{
        background: transparent !important;
        border: 1px solid {T['strong_border']} !important;
        color: {T['text']} !important;
    }}
    .st-key-kk-result-actions [data-testid="stPopover"] button:hover {{
        border-color: {T['accent']} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="kk-result-actions"):
        f1, f2, f3, f4 = st.columns(4, gap="medium", vertical_alignment="center")

        with f1:
            if st.button("진행 중으로 저장", key=f"keep-{exp_id}", **ui.WIDE):
                db.update_experiment(exp_id, {"note": note, "status": "진행 중"})
                st.toast("메모가 저장되었으며 실험 상태는 진행 중으로 유지됩니다.")

        with f2:
            if st.button("+ 새 실험 설계", key="new-exp", **ui.WIDE):
                st.switch_page(ui.PAGE_FILES["marketing"])

        with f3:
            with st.popover("실험 삭제", use_container_width=True):
                st.warning("실험과 배정 명단이 영구 삭제됩니다.")
                sure = st.checkbox("삭제에 동의합니다.", key=f"sure-{exp_id}")
                if st.button("삭제 확인", key=f"del-{exp_id}", disabled=not sure, type="primary", **ui.WIDE):
                    db.delete_experiment(exp_id)
                    ss.pop("exp_pick", None)
                    st.rerun()

        with f4:
            if st.button("판정 저장하고 라이브러리로 →", type="primary", key=f"save-{exp_id}", **ui.WIDE,
                         disabled=test is None):
                db.update_experiment(exp_id, {
                    "obs_n_treat": test["n_t"], "obs_x_treat": test["x_t"],
                    "obs_n_ctrl": test["n_c"], "obs_x_ctrl": test["x_c"],
                    "p_value": test["p_value"], "ci_low": test["ci_low"], "ci_high": test["ci_high"],
                    "verdict": verdict, "is_simulated": 1 if demo else 0,
                    "status": "완료", "note": note,
                })
                st.switch_page(ui.PAGE_FILES["library"])



# ─────────────────────────────────────────────
ui.render_header()

if ss.get("_toast"):
    st.toast(ss.pop("_toast"))

with st.container(key="kk-body"):
    strategy, match = ss.get("strategy"), ss.get("match")
    can_design = bool(strategy and match)
    st.markdown(ui.compact(ui.steps_html(3)), unsafe_allow_html=True)

    views = (["새 실험 설계"] if can_design else []) + ["실험 목록 · 결과 입력"]
    wanted = "새 실험 설계" if ss.get("exp_view") == "design" and can_design else "실험 목록 · 결과 입력"
    if ss.get("exp_tab") not in views or ss.get("exp_view_applied") != ss.get("exp_view"):
        ss["exp_tab"] = wanted
        ss["exp_view_applied"] = ss.get("exp_view")
    if ss.get("open_exp") is not None:            # 다른 화면에서 특정 실험을 열라고 보낸 경우
        ss["exp_tab"] = "실험 목록 · 결과 입력"
    view = ui.choose("보기", views, "exp_tab", wanted, label_visibility="collapsed") or wanted

    if view == "새 실험 설계":
        ui.html(ui.context_html(strategy, seg_display(match["segment"]), "설계 중"))
        design_view(strategy, match)
    else:
        result_view()
