import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from io import BytesIO

st.title("CV Analyzer — Flexible (treatment or concentration)")

uploaded_files = st.file_uploader("Upload CV .txt files", accept_multiple_files=True, type=["txt"])

if not uploaded_files:
    st.info("Upload minimal 1 file .txt (format: t, E, I).")
    st.stop()

# read all files
data = {}
filenames = []
for f in uploaded_files:
    label = f.name.rsplit(".",1)[0]
    filenames.append(label)
    df = pd.read_csv(f, header=None, names=["t","E","I"])
    data[label] = df

# Option: use filename as label (always true) and optional auto-extract concentration
st.sidebar.header("Options")
use_filename_labels = st.sidebar.checkbox("Gunakan nama file sebagai label (default)", value=True)
enable_autoconc = st.sidebar.checkbox("Coba ekstrak konsentrasi dari nama file (xxmm)", value=True)
enable_calibration = st.sidebar.checkbox("Buat kurva kalibrasi? (harus isi konsentrasi)", value=False)

# Try auto-extract concentrations
concs_auto = {}
if enable_autoconc:
    for label in filenames:
        m = re.search(r'(\d+(\.\d+)?)\s*mm', label.lower())
        if m:
            concs_auto[label] = float(m.group(1))

# Show UI to input manual concentrations (only when calibration requested)
concs_manual = {}
if enable_calibration:
    st.subheader("Masukkan konsentrasi (mM) untuk file yang ingin dipakai kalibrasi")
    for label in filenames:
        default_val = concs_auto.get(label, "")
        inp = st.text_input(f"Konsentrasi untuk {label} (kosong = tidak ikut kalibrasi)", value=str(default_val), key="c_"+label)
        if inp.strip() != "":
            try:
                concs_manual[label] = float(inp)
            except:
                st.error(f"Nilai untuk {label} bukan angka valid")

# --- Overlay plot (always)
st.subheader("Overlay CV")
fig, ax = plt.subplots(figsize=(7,5))
for label, df in data.items():
    ax.plot(df["E"], df["I"], label=label)
ax.set_xlabel("E (V)"); ax.set_ylabel("I (µA)")
ax.legend(); ax.grid(True)
st.pyplot(fig)

# --- Calibration (only if requested and at least 2 concs provided)
if enable_calibration:
    if len(concs_manual) < 2:
        st.warning("Perlu minimal 2 file dengan konsentrasi untuk membuat kurva kalibrasi.")
    else:
        # prepare arrays
        concs = []
        ox_peaks = []
        red_peaks = []
        # windows (adjustable or hardcode as before)
        ox_window = (0.37, 0.47)
        red_window = (0.0, 0.1)
        for label, conc in concs_manual.items():
            df = data[label]
            concs.append(conc)
            ox_df = df[(df["E"]>ox_window[0]) & (df["E"]<ox_window[1])]
            red_df = df[(df["E"]>red_window[0]) & (df["E"]<red_window[1])]
            ox_peaks.append(ox_df["I"].max())
            red_peaks.append(red_df["I"].min())

        # sort by concentration
        order = np.argsort(concs)
        concs = np.array(concs)[order]
        ox_peaks = np.array(ox_peaks)[order]
        red_peaks = np.array(red_peaks)[order]

        # linear fit oxidation
        m_ox, b_ox = np.polyfit(concs, ox_peaks, 1)
        r2_ox = np.corrcoef(concs, ox_peaks)[0,1]**2

        st.subheader("Kalibrasi Oksidasi")
        fig2, ax2 = plt.subplots()
        ax2.scatter(concs, ox_peaks, color="red")
        ax2.plot(concs, m_ox*concs+b_ox, "r--")
        ax2.set_xlabel("Concentration (mM)"); ax2.set_ylabel("Peak I (µA)")
        ax2.set_title(f"I = {m_ox:.3f} C + {b_ox:.3f}, R2={r2_ox:.3f}")
        st.pyplot(fig2)

        # linear fit reduction
        m_red, b_red = np.polyfit(concs, red_peaks, 1)
        r2_red = np.corrcoef(concs, red_peaks)[0,1]**2

        st.subheader("Kalibrasi Reduksi")
        fig3, ax3 = plt.subplots()
        ax3.scatter(concs, red_peaks, color="blue")
        ax3.plot(concs, m_red*concs+b_red, "b--")
        ax3.set_xlabel("Concentration (mM)"); ax3.set_ylabel("Peak I (µA)")
        ax3.set_title(f"I = {m_red:.3f} C + {b_red:.3f}, R2={r2_red:.3f}")
        st.pyplot(fig3)

        # offer excel download
        compiled_df = pd.DataFrame({"Concentration (mM)": concs, "Ox Peak": ox_peaks, "Red Peak": red_peaks})
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            compiled_df.to_excel(writer, index=False, sheet_name="Calibration")
        buffer.seek(0)
        st.download_button("Download calibration Excel", data=buffer, file_name="calibration.xlsx")
