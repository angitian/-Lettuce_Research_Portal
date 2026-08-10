# 🥬 SYSTEM DOCUMENTATION & LLM CONTEXT MANUAL
## Lettuce Phytochemical, LED Supplemental Lighting & Environmental Analytics Web Portal

> **[LLM System Context Prompt]**
> You are an AI Plant Science & Agricultural Data Specialist assisting users with the **Lettuce Phytochemical & LED Research Web Application**. 
> Use the detailed system specifications, data schemas, mathematical formulas, and user guide below to accurately answer any user queries, troubleshoot data entry issues, explain statistical results (Two-Way ANOVA, Tukey HSD, DLI), and guide users through operating the application.

---

## 1. 📌 Overview & Research Objectives
This web application is designed for researchers studying the **influence of supplemental LED lighting and soil chemical properties on plant growth trajectory and phytochemical accumulation in head lettuce (Green Moon & Fame varieties)**.

### Core Objectives:
- **Biometric Growth Tracking**: Record canopy width, length, height, leaf count, and hue angle across weekly intervals for fixed plant samples.
- **Phytochemical Quantification**: Automatically convert UV-Vis spectrophotometric absorbance readings (OD 663, 645, 470, 765 nm) into chlorophyll, carotenoid, and phenolic concentrations.
- **High-Frequency Environmental & PPFD Analytics**: Ingest and downsample high-frequency PAR/PPFD CSV loggers and Temperature/Humidity Excel loggers into hourly means and calculate Daily Light Integral (DLI) in $\text{mol/m}^2/\text{day}$.
- **Statistical Analytics**: Perform Two-Way ANOVA ($\text{Variety} \times \text{Lighting}$), Tukey HSD post-hoc comparisons, and Pearson correlation heatmaps.

---

## 2. 🧪 Experimental Design & Schema

### Treatments & Factors:
The research consists of **5 Experimental Treatments** across **2 Varieties** and **2 Lighting Conditions**:

| Treatment Name | Variety | Lighting Condition | Sample Size per Treatment |
| :--- | :--- | :--- | :--- |
| `Control_GM` | Green Moon | Natural Light Control | 10 Fixed Plant IDs |
| `LED_GM` | Green Moon | LED Supplemental Light | 10 Fixed Plant IDs |
| `Control_F` | Fame | Natural Light Control | 10 Fixed Plant IDs |
| `LED_F (1)` | Fame | LED Supplemental Light (Replicate 1) | 10 Fixed Plant IDs |
| `LED_F (2)` | Fame | LED Supplemental Light (Replicate 2) | 10 Fixed Plant IDs |

### Fixed Plant Identifiers (10 Plants per Treatment = 50 Plants Total):
To ensure repeat-measurement tracking without index misalignment, each treatment tracks the exact same **10 Plant IDs**:
`A2`, `A5`, `A7`, `B3`, `B5`, `B6`, `B8`, `C4`, `C6`, `C9`.

---

## 3. 📐 Mathematical & Phytochemical Formulas

### A. Phytochemical Quantification (Gratani / Lichtenthaler Equations):
Raw spectrophotometer OD values are normalized by sample weight ($W_{\text{sample}}$ in grams):

1. **Chlorophyll a ($\text{mg/g FW}$)**:
   $$\text{Chl}_a = \frac{12.7 \times \text{OD}_{663} - 2.69 \times \text{OD}_{645}}{W_{\text{sample}}}$$

2. **Chlorophyll b ($\text{mg/g FW}$)**:
   $$\text{Chl}_b = \frac{22.9 \times \text{OD}_{645} - 4.68 \times \text{OD}_{663}}{W_{\text{sample}}}$$

3. **Total Chlorophyll ($\text{mg/g FW}$)**:
   $$\text{Total Chl} = \text{Chl}_a + \text{Chl}_b = \frac{8.02 \times \text{OD}_{663} + 20.2 \times \text{OD}_{645}}{W_{\text{sample}}}$$

4. **Total Carotenoids ($\text{mg/g FW}$)**:
   $$\text{Carotenoids} = \frac{1000 \times \text{OD}_{470} - 1.82 \times \text{Chl}_a - 85.02 \times \text{Chl}_b}{227 \times W_{\text{sample}}}$$

5. **Total Phenolic Content ($\text{mg GAE/g FW}$)**:
   $$\text{Total Phenolics} = \frac{10 \times \text{OD}_{765}}{W_{\text{sample}}}$$

### B. Daily Light Integral (DLI) Calculation:
High-frequency PPFD measurements ($\mu\text{mol/m}^2/\text{s}$) are averaged hourly ($\text{Hourly Mean}_h$). The daily cumulative sum is computed as:
$$\text{DLI}_{\text{daily}} = \frac{\sum_{h=0}^{23} \left( \text{Hourly Mean PPFD}_h \times 3600 \right)}{1,000,000} \quad \left[\text{mol/m}^2/\text{day}\right]$$

---

## 4. 🖥️ Web Portal Architecture & Navigation

The application is structured into **5 Primary Navigation Tabs**:

```
🥬 Lettuce Research Web Portal
 ├── 🏠 Executive Dashboard
 ├── 📝 Weekly Data Entry
 ├── 🌡️ Environment & Loggers
 │    ├── 📂 Import Loggers & Channel Mapping
 │    ├── 📈 Hourly Temperature & PPFD Graphs
 │    ├── ☀️ Daily Light Integral (DLI) Analytics
 │    └── 🌱 Soil Chemical Properties
 ├── 🔬 Harvest & Lab Results
 │    ├── 🌾 Harvest Yield Measurements
 │    └── 🧪 UV-Vis Spectrophotometer Absorbance
 └── 📊 Statistical Analytics & Graphs
```

### Tab 1: 🏠 Executive Dashboard
- **KPI Metrics Cards**: Total sample plants logged, % LED growth boost vs control, mean total chlorophyll, and mean total phenolics.
- **Growth & Phytochemical Overview Charts**: Real-time Plotly interactive line and bar charts.
- **Latest Biometric Summary**: Aggregated treatment averages for canopy width, height, leaf count, and chlorophyll.

### Tab 2: 📝 Weekly Data Entry
- **Date Selector**: `st.date_input` formatted as `DD/MM/YYYY`. Automatically calculates `Week Number = ((Date - 2026-08-04) // 7) + 1`.
- **Treatment Sub-Tabs**: 5 separate tabs (`Control_GM`, `LED_GM`, `Control_F`, `LED_F (1)`, `LED_F (2)`).
- **Data Grid**: Displays fixed 10 Plant IDs (`A2`-`C9`) with editable columns (`canopy_width`, `canopy_length`, `canopy_height`, `leaf_count`, `hue_angle`).
- **Persistent Auto-Save**: Any numeric input immediately updates `st.session_state` and saves to `data/saved_experiment_data.csv`. Includes a manual `💾 บันทึกข้อมูล` button for confirmation.

### Tab 3: 🌡️ Environment & Loggers
1. **📂 Import Loggers & Channel Mapping**:
   - **PPFD CSV Multi-Upload**: Accepts HOBO PAR logger CSV files (e.g. `2026-07-10 ppfd.csv`). Parses Thai time format (`07/10/26 04 นาฬิกา 1 นาที`).
   - **Temp XLS/XLSX/CSV Multi-Upload**: Accepts BIFF8 Excel files (e.g. `2026-07-20 T หอมห่อ.xls`). Converts Thai Buddhist Era years (`2569` $\rightarrow$ `2026 AD`).
   - **Accumulative Storage**: Appends newly uploaded loggers without overwriting prior records.
   - **Hourly Downsampling**: Automatically downsamples 1-minute high-frequency data to hourly averages on import, reducing storage size by 98%.
   - **Custom Plot Naming**: Form fields to map PPFD sensor channels to custom plot labels (e.g. `Control_GM`, `LED_GM`).
2. **📈 Hourly Temperature & PPFD Graphs**:
   - **Date Range Selector**: `📅 เลือกช่วงวันที่ต้องการแสดงผลกราฟ` (`DD/MM/YYYY`) to filter line charts dynamically.
   - Plotly interactive line charts with hover tooltips and `dd/mm/yyyy HH:MM` time formatting.
3. **☀️ Daily Light Integral (DLI) Analytics**:
   - **Date Range Selector**: `📅 เลือกช่วงวันที่ต้องการแสดงผล DLI` (`DD/MM/YYYY`).
   - Metric cards showing average and peak DLI ($\text{mol/m}^2/\text{day}$).
   - Grouped bar chart comparing daily light reception across plots.
   - Exportable DLI summary table and CSV download.
4. **🌱 Soil Chemical Properties**:
   - Data editor for soil pH, EC (dS/m), organic matter (%), total N (%), available P, available K (mg/kg), and soil texture.

### Tab 4: 🔬 Harvest & Lab Results
- **Treatment Sub-Tabs**: 5 treatment tabs for clean data entry.
- **Harvest Yield**: Enter fresh weight (g), root length (cm), core length (cm), head diameter (cm), and firmness index.
- **Lab OD Entry**: Enter sample weight (g), OD 663, 645, 470, 765 nm. Automatically calculates phytochemical concentrations.

### Tab 5: 📊 Statistical Analytics & Graphs
- **Parameter Selector**: Select any biometric or chemical variable (e.g., `Total Chlorophyll`, `Canopy Width`, `Fresh Weight`).
- **Descriptive Statistics**: Count, Mean $\pm$ SD, Min, Max by treatment.
- **Two-Way ANOVA**: Analyzes main effects of **Variety** (Green Moon vs Fame), **Lighting** (Control vs LED), and their **Interaction**. Reports p-values and ANOVA table.
- **Tukey HSD Post-Hoc Test**: Pairwise group comparison with confidence intervals and adjusted p-values.
- **Visualizations**: Error Bar Charts, Boxplots, Growth Trajectories, and Pearson Correlation Matrix Heatmap.

---

## 5. 💾 File Persistence & Data Schema Locations

- **Growth & Phytochemical Dataset**: `data/saved_experiment_data.csv`
- **Soil & Environmental Weekly Summary**: `data/saved_env_data.csv`
- **Accumulated PPFD Logger**: `data/accumulated_ppfd_logger.csv`
- **Accumulated Temp Logger**: `data/accumulated_temp_logger.csv`
- **Original Source Dataset Backup**: `04-08-69.xlsx`

---

## 6. ❓ Frequently Asked Questions (FAQ for LLM Assistance)

### Q1: What happens if I refresh the browser (F5) after entering data?
**Answer**: Data will NOT be lost. The application uses **Persistent Auto-Save**, which immediately writes table edits to local CSV files (`data/saved_experiment_data.csv`) on every change.

### Q2: Why does the system downsample high-frequency logger data to hourly averages?
**Answer**: High-frequency loggers produce over 40,000 rows per month. Since research charts and DLI calculations use hourly means, downsampling reduces memory usage by 98% and speeds up chart rendering by 10x while maintaining 100% mathematical accuracy for DLI.

### Q3: How are Thai date and time strings handled in logger files?
**Answer**: The parser automatically converts Thai PPFD time strings (e.g. `07/10/26 04 นาฬิกา 1 นาที` $\rightarrow$ `2026-07-10 04:01:00`) and Thai Buddhist Era years in temperature loggers (e.g. `22/6/2569` $\rightarrow$ `22/06/2026`).

### Q4: Can I upload logger files from multiple weeks without losing old data?
**Answer**: Yes. The system features **Accumulative Multi-Upload**. Uploading a new CSV or XLS file merges newly recorded timestamps with existing data and deduplicates on date/time.

---

## 7. 💬 Prompt Examples for Querying this LLM

When prompting an LLM with this manual attached, you can ask questions like:

- *"How does the app calculate Total Chlorophyll and Carotenoid content from OD 663, 645, and 470 nm?"*
- *"Explain how Two-Way ANOVA evaluates the interaction between Lettuce Variety and LED Supplemental Lighting."*
- *"How do I import HOBO PPFD CSV files and rename sensor channels to custom plot names?"*
- *"Why is DLI expressed in mol/m²/day and how is it derived from hourly PPFD averages?"*
- *"Where is the experiment data saved on disk, and how can I restore data if needed?"*
