import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import io
from functools import reduce

st.title("⚡ Cyclic Voltammetry Analyzer")

uploaded_files = st.file_uploader(
    "Upload file CV (.txt)", type=["txt"], accept_multiple_files=True
)

data_dict = {}

if uploaded_files:
    fig, ax = plt.subplots()

    for file in uploaded_files:
        # Baca data
        df = pd.read_csv(file, delim_whitespace=True, header=None)
        df = df.rename(columns={1: "E", 2: "I"})[["E", "I"]]
        data_dict[file.name] = df

        ax.plot(df["E"], df["I"], label=file.name)

    ax.set_xlabel("Potential (V)")
    ax.set_ylabel("Current (µA)")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # -----------------------------
    # Kurva kalibrasi (ambil puncak oksidasi & reduksi)
    # -----------------------------
    concentrations = []
    ox_peaks = []
    red_peaks = []

    for name, df in data_dict.items():
        # Ambil angka konsentrasi dari nama file (misal "10mm")
        match = re.search(r"(\d+)\s*mm", name, re.IGNORECASE)
        if match:
            conc = float(match.group(1))
            concentrations.append(conc)

            # Cari puncak oksidasi (positif, sekitar 0.42V)
            ox_region = df[(df["E"] > 0.3) & (df["E"] < 0.6)]
            ox_peak = ox_region["I"].max() if not ox_region.empty else np.nan
            ox_peaks.append(ox_peak)

            # Cari puncak reduksi (negatif, sekitar 0.05V)
            red_region = df[(df["E"] > -0.1) & (df["E"] < 0.2)]
            red_peak = red_region["I"].min() if not red_region.empty else np.nan
            red_peaks.append(red_peak)

    if concentrations:
        # Dataframe kalibrasi
        calib_df = pd.DataFrame({
            "Concentration (mM)": concentrations,
            "Oxidation Peak (µA)": ox_peaks,
            "Reduction Peak (µA)": red_peaks
        })

        st.subheader("📈 Calibration Curves")

        # Oksidasi
        fig_ox, ax_ox = plt.subplots()
        ax_ox.scatter(concentrations, ox_peaks, color="red", label="Oxidation")
        m, b = np.polyfit(concentrations, ox_peaks, 1)
        ax_ox.plot(concentrations, m*np.array(concentrations)+b, "--", color="black")
        ax_ox.set_xlabel("Concentration (mM)")
        ax_ox.set_ylabel("Oxidation Peak (µA)")
        ax_ox.legend()
        st.pyplot(fig_ox)

        # Reduksi
        fig_red, ax_red = plt.subplots()
        ax_red.scatter(concentrations, red_peaks, color="blue", label="Reduction")
        m, b = np.polyfit(concentrations, red_peaks, 1)
        ax_red.plot(concentrations, m*np.array(concentrations)+b, "--", color="black")
        ax_red.set_xlabel("Concentration (mM)")
        ax_red.set_ylabel("Reduction Peak (µA)")
        ax_red.legend()
        st.pyplot(fig_red)

        # Tombol download kalibrasi
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            calib_df.to_excel(writer, sheet_name="Calibration", index=False)
        st.download_button(
            "📥 Download Calibration Data (Excel)",
            buffer.getvalue(),
            file_name="calibration_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # -----------------------------
    # Overlay data mentah (gabung 1 sheet)
    # -----------------------------
    if data_dict:
        merged = []
        for name, df in data_dict.items():
            df_renamed = df.rename(columns={"I": f"I_{name}"})
            merged.append(df_renamed)

        df_merged = reduce(lambda left, right: pd.merge(left, right, on="E", how="outer"), merged)
        df_merged = df_merged.sort_values(by="E")

        buffer2 = io.BytesIO()
        with pd.ExcelWriter(buffer2, engine="xlsxwriter") as writer:
            df_merged.to_excel(writer, sheet_name="Overlay", index=False)

        st.download_button(
            "📥 Download Overlay Data (Excel, 1 Sheet)",
            buffer2.getvalue(),
            file_name="overlay_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
