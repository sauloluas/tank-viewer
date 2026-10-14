import time
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Simulador de Tanques", layout="wide")

# ==================== PARÂMETROS DO PROCESSO ====================
CAP_A                = 20.0   # Capacidade do Tanque A (L)
CAP_B                = 12.0   # Capacidade do Tanque B (L)

VOL_A_INICIAL        = 0.60    # Fração inicial do Tanque A
VOL_B_INICIAL        = 0.20    # Fração inicial do Tanque B

Q_BOMBA_MAX          = 8.0    # Vazão máx. da bomba (L/min)
Q_RETORNO_MAX        = 6.0    # Vazão máx. do retorno por gravidade (L/min)
POTENCIA_BOMBA_PCT   = 80      # Potência da bomba (%)
ABERTURA_VALVULA_PCT = 50      # Abertura da válvula de retorno (%)

SP_B_MIN             = 40      # Setpoint inferior do Tanque B (%)
SP_B_MAX             = 70      # Setpoint superior do Tanque B (%)
SP_B_MAX_L           = 8.4
SP_B_MIN_L           = 4.8

DT_SUB_MAX_S         = 0.5     # Subpasso máximo (s simulados)
HIST_MAXLEN          = 480     # Pontos no histórico
SIM_SAMPLE_INTERVAL  = 1.0    # NOVO: s simulados entre pontos do gráfico

# ================================================================


st.title("Sistema de Tanques de Água")

# ---------------------------------------------------------- estado
if "vol_a" not in st.session_state:
    st.session_state.vol_a      = CAP_A * VOL_A_INICIAL
    st.session_state.vol_b      = CAP_B * VOL_B_INICIAL
    st.session_state.bomba      = False
    st.session_state.rodando    = True
    st.session_state.hist       = []
    st.session_state.t_ant      = time.monotonic()
    st.session_state.velocidade = 1
    st.session_state.t_sim      = 0.0      # NOVO: relógio simulado
    st.session_state.hist       = []
    st.session_state.hist_acc   = 0.0      # NOVO: acumulador de amostragem



def resetar():
    st.session_state.vol_a      = CAP_A * VOL_A_INICIAL
    st.session_state.vol_b      = CAP_B * VOL_B_INICIAL
    st.session_state.bomba      = False
    st.session_state.rodando    = True
    st.session_state.hist       = []
    st.session_state.t_ant      = time.monotonic()
    st.session_state.t_sim      = 0.0      # NOVO
    st.session_state.hist       = []
    st.session_state.hist_acc   = 0.0      # NOVO



# ------------------------------------------------------------------ desenho
def svg_processo(vol_a, vol_b, bomba_on, retorno_ativo):
    fa = max(0.0, min(1.0, vol_a / CAP_A if CAP_A else 0.0))
    fb = max(0.0, min(1.0, vol_b / CAP_B if CAP_B else 0.0))

    # Tanque A (retangular)
    A_X, A_Y, A_W, A_H = 60.0, 220.0, 250.0, 180.0
    A_BOT  = A_Y + A_H
    A_AGUA = A_BOT - A_H * fa

    # Tanque B (cilíndrico)
    B_CX, B_RX, B_RY = 700.0, 110.0, 20.0
    B_TOP, B_BOT = 110.0, 400.0
    B_L, B_R = B_CX - B_RX, B_CX + B_RX
    B_H = B_BOT - B_TOP
    B_AGUA = B_BOT - B_H * fb

    sp_hi_y = B_BOT - B_H * (SP_B_MAX / 100.0)
    sp_lo_y = B_BOT - B_H * (SP_B_MIN / 100.0)

    corpo_b = (f"M {B_L:.0f} {B_TOP:.0f} L {B_L:.0f} {B_BOT:.0f} "
               f"A {B_RX:.0f} {B_RY:.0f} 0 0 0 {B_R:.0f} {B_BOT:.0f} "
               f"L {B_R:.0f} {B_TOP:.0f} Z")

    rec = "M 123 348 L 123 70 L 700 70 L 700 142"
    ret = "M 745 405 L 745 478 L 285 478 L 285 402"

    cor_bomba = "#43A047" if bomba_on else "#90A4AE"
    cls_bomba = ' class="pulsar"' if bomba_on else ""

    out = []
    o = out.append

    o('<style>'
      '@keyframes fluxoAB { to { stroke-dashoffset: -28; } }'
      '.fluxo { stroke-dasharray: 10 18; animation: fluxoAB 1s linear infinite; }'
      '@keyframes pulsar { 0%,100% { opacity: 1; } 50% { opacity: .35; } }'
      '.pulsar { animation: pulsar 1s ease-in-out infinite; }'
      '</style>')

    o('<svg viewBox="0 0 1020 540" width="100%" '
      'style="max-width:1080px;display:block;margin:0 auto" '
      'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">')

    o('<defs>')
    o(f'<clipPath id="clipB"><path d="{corpo_b}"/></clipPath>')
    o('<linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0%" stop-color="#64B5F6"/>'
      '<stop offset="100%" stop-color="#1565C0"/></linearGradient>')
    o('<linearGradient id="gB" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0%" stop-color="#4DB6AC"/>'
      '<stop offset="100%" stop-color="#00695C"/></linearGradient>')
    o('</defs>')

    # ---------------- Tanque A ----------------
    o(f'<rect x="{A_X:.0f}" y="{A_Y:.0f}" width="{A_W:.0f}" height="{A_H:.0f}" rx="10" '
      f'fill="#EDF3F6" stroke="#8A9BA8" stroke-width="4"/>')
    if fa > 0.002:
        base = A_BOT - 3
        o(f'<rect x="{A_X+3:.0f}" y="{A_AGUA:.1f}" width="{A_W-6:.0f}" '
          f'height="{base-A_AGUA:.1f}" fill="url(#gA)" opacity="0.92"/>')
        o(f'<rect x="{A_X+3:.0f}" y="{A_AGUA:.1f}" width="{A_W-6:.0f}" height="5" '
          f'fill="#B3E5FC" opacity="0.85"/>')
    o(f'<text x="{A_X+A_W/2:.0f}" y="{A_Y-14:.0f}" text-anchor="middle" font-size="18" '
      f'font-weight="700" fill="#37474F">Tanque A</text>')
    o(f'<text x="{A_X+A_W/2:.0f}" y="{A_BOT+42:.0f}" text-anchor="middle" font-size="19" '
      f'font-weight="700" fill="#1565C0">{vol_a:,.1f} L</text>')

    # ---------------- Tanque B ----------------
    o(f'<path d="{corpo_b}" fill="#EDF3F6"/>')
    if fb > 0.002:
        o('<g clip-path="url(#clipB)">')
        o(f'<rect x="{B_L:.0f}" y="{B_AGUA:.1f}" width="{2*B_RX:.0f}" '
          f'height="{B_BOT+B_RY+10-B_AGUA:.1f}" fill="url(#gB)" opacity="0.92"/>')
        o(f'<ellipse cx="{B_CX:.0f}" cy="{B_AGUA:.1f}" rx="{B_RX:.0f}" ry="{B_RY:.0f}" '
          f'fill="#4DB6AC" opacity="0.95"/>')
        o('</g>')

    o(f'<path d="{corpo_b}" fill="none" stroke="#8A9BA8" stroke-width="4"/>')
    o(f'<ellipse cx="{B_CX:.0f}" cy="{B_TOP:.0f}" rx="{B_RX:.0f}" ry="{B_RY:.0f}" '
      f'fill="none" stroke="#8A9BA8" stroke-width="4"/>')

    # setpoints
    o('<g clip-path="url(#clipB)">')
    o(f'<ellipse cx="{B_CX:.0f}" cy="{sp_hi_y:.1f}" rx="{B_RX:.0f}" ry="{B_RY:.0f}" '
      f'fill="none" stroke="#E53935" stroke-width="2.5" '
      f'stroke-dasharray="9 7" opacity="0.95"/>')
    o(f'<ellipse cx="{B_CX:.0f}" cy="{sp_lo_y:.1f}" rx="{B_RX:.0f}" ry="{B_RY:.0f}" '
      f'fill="none" stroke="#FB8C00" stroke-width="2.5" '
      f'stroke-dasharray="9 7" opacity="0.95"/>')
    o('</g>')

    o(f'<text x="{B_R + 14:.0f}" y="{sp_hi_y + 5:.1f}" font-size="13" '
        f'font-weight="700" fill="#E53935">SP máx — {SP_B_MAX} ({SP_B_MAX_L} L)%</text>')
    o(f'<text x="{B_R + 14:.0f}" y="{sp_lo_y + 5:.1f}" font-size="13" '
      f'font-weight="700" fill="#FB8C00">SP mín — {SP_B_MIN} ({SP_B_MIN_L} L)%</text>')

    o(f'<text x="{B_L-20:.0f}" y="205" text-anchor="end" font-size="18" '
      f'font-weight="700" fill="#37474F">Tanque B</text>')
    o(f'<text x="{B_CX:.0f}" y="452" text-anchor="middle" font-size="19" '
      f'font-weight="700" fill="#00695C">{vol_b:,.1f} L</text>')

    # ---------------- bomba ----------------
    o(f'<g{cls_bomba}>')
    o(f'<rect x="92" y="348" width="62" height="42" rx="9" fill="{cor_bomba}" '
      f'stroke="#37474F" stroke-width="3"/>')
    o('<circle cx="123" cy="369" r="11" fill="#ECEFF1" stroke="#37474F" stroke-width="2"/>')
    o('<path d="M 123 360 L 123 378 M 114 369 L 132 369" stroke="#37474F" '
      'stroke-width="2" stroke-linecap="round"/>')
    o('</g>')
    o('<text x="123" y="414" text-anchor="middle" font-size="13" font-weight="700" '
      'fill="#37474F">BOMBA</text>')

    # jato caindo no Tanque B
    if bomba_on and B_AGUA > 150:
        o(f'<line x1="700" y1="142" x2="700" y2="{B_AGUA:.0f}" stroke="#4FC3F7" '
          f'stroke-width="6" stroke-linecap="round" class="fluxo"/>')

    # mangueira de recalque
    o(f'<path d="{rec}" fill="none" stroke="#455A64" stroke-width="16" '
      f'stroke-linecap="round" stroke-linejoin="round"/>')
    if bomba_on:
        o(f'<path d="{rec}" fill="none" stroke="#29B6F6" stroke-width="8" '
          f'stroke-linecap="round" stroke-linejoin="round" class="fluxo"/>')

    # mangueira de retorno
    o(f'<path d="{ret}" fill="none" stroke="#455A64" stroke-width="16" '
      f'stroke-linecap="round" stroke-linejoin="round"/>')
    if retorno_ativo:
        o(f'<path d="{ret}" fill="none" stroke="#26A69A" stroke-width="8" '
          f'stroke-linecap="round" stroke-linejoin="round" class="fluxo"/>')

    o('</svg>')
    return "\n".join(out)


# ------------------------------------------------------------------ painel
@st.fragment(run_every="1s")
def painel():
    agora = time.monotonic()
    dt = min(max(agora - st.session_state.t_ant, 0.0), 2.5)
    st.session_state.t_ant = agora

    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        rotulo = "⏹️ Desligar bomba" if st.session_state.bomba else "▶️ Ligar bomba"
        if st.button(rotulo, use_container_width=True, key="btn_bomba"):
            st.session_state.bomba = not st.session_state.bomba

    with c2:
        st.session_state.rodando = st.toggle(
            "Simulação em execução",
            value=st.session_state.rodando,
            key="tg_rodando",
        )

    with c3:
        vel = st.segmented_control(
            "Velocidade",
            options=[1, 2, 5, 10, 20],
            format_func=lambda v: f"{v}×",
            selection_mode="single",
            key="velocidade",
        )
        if vel is None:
            vel = 1
            st.session_state.velocidade = 1

    # ---------------- modelo físico ----------------
    q_bomba_nom = Q_BOMBA_MAX * (POTENCIA_BOMBA_PCT / 100.0) if st.session_state.bomba else 0.0

    dt_sim_s   = dt * vel
    n_sub      = max(1, int(dt_sim_s / DT_SUB_MAX_S) + 1)
    dt_sub_min = (dt_sim_s / n_sub) / 60.0
    q_retorno = 0.0
    if st.session_state.rodando and dt_sub_min > 0:
        t_sim    = st.session_state.t_sim
        hist_acc = st.session_state.hist_acc
        dt_sub_s = dt_sub_min * 60.0        # subpasso em segundos simulados

        for _ in range(n_sub):
            frac_b = st.session_state.vol_b / CAP_B if CAP_B else 0.0
            q_retorno = Q_RETORNO_MAX * (ABERTURA_VALVULA_PCT / 100.0) * (max(frac_b, 0.0) ** 0.5)

            v_recalque = min(q_bomba_nom * dt_sub_min,
                             st.session_state.vol_a,
                             max(CAP_B - st.session_state.vol_b, 0.0))
            v_retorno  = min(q_retorno * dt_sub_min, st.session_state.vol_b)

            st.session_state.vol_a += v_retorno - v_recalque
            st.session_state.vol_b += v_recalque - v_retorno

            # ---- relógio + amostragem em tempo simulado ----
            t_sim    += dt_sub_s
            hist_acc += dt_sub_s
            if hist_acc >= SIM_SAMPLE_INTERVAL:
                hist_acc -= SIM_SAMPLE_INTERVAL
                st.session_state.hist.append({
                    "t (s)":        round(t_sim, 2),
                    "Tanque A (L)": round(st.session_state.vol_a, 2),
                    "Tanque B (L)": round(st.session_state.vol_b, 2),
                })

        st.session_state.t_sim    = t_sim
        st.session_state.hist_acc = hist_acc
        st.session_state.hist     = st.session_state.hist[-HIST_MAXLEN:]

        if st.session_state.vol_a > CAP_A:
            st.session_state.vol_a = CAP_A


    # ---------------- desenho ----------------
    st.markdown(
        svg_processo(
            st.session_state.vol_a,
            st.session_state.vol_b,
            st.session_state.bomba,
            q_retorno > 0.01,
        ),
        unsafe_allow_html=True,
    )

    # ---------------- indicadores ----------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tanque A", f"{st.session_state.vol_a:,.1f} L")
    m2.metric("Tanque B", f"{st.session_state.vol_b:,.1f} L")
    m3.metric("Vazão de recalque", f"{q_bomba_nom:,.1f} L/min")
    m4.metric("Vazão de retorno", f"{q_retorno:,.1f} L/min")

    # ---------------- histórico ----------------
    st.session_state.hist.append({
        "Tanque A (L)": round(st.session_state.vol_a, 2),
        "Tanque B (L)": round(st.session_state.vol_b, 2),
    })
    st.session_state.hist = st.session_state.hist[-HIST_MAXLEN:]
    if st.session_state.hist:
        df = pd.DataFrame(st.session_state.hist).set_index("t (s)")
        st.line_chart(df, height=240)


painel()
