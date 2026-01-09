# 🚀 本地测试指南

## 📋 步骤1：训练模型

首先需要训练模型并保存模型文件：

```bash
cd scripts
python train_model.py
```

这会创建：
- `models/kmeans_model.pkl` - 训练好的K-Means模型
- `models/scaler.pkl` - 特征标准化器
- `models/feature_names.txt` - 特征名称列表
- `data/processed/regime_labels_new.csv` - 历史regime标签

**预期输出**：
```
==================================================
Training Market Regime Identification Model
==================================================

1. Loading data...
   Loaded XXXX rows from 2018-XX-XX to 2024-XX-XX

2. Engineering features...
   Created features: ret_btc, vol_btc_7, fg_norm, pct_above_ma50
   After cleaning: XXXX rows

3. Standardizing features...
   Feature means: [...]
   Feature stds:  [...]

4. Training K-Means (k=2)...
   Silhouette Score: 0.2861

5. Cluster characteristics:
   [显示两个聚类的特征统计]

6. Saving model artifacts...
   ✓ Saved kmeans_model.pkl
   ✓ Saved scaler.pkl
   ✓ Saved feature_names.txt
   ✓ Saved regime_labels_new.csv

✅ Model training complete!
```

---

## 📋 步骤2：生成Dashboard数据

运行daily_update.py生成JSON数据：

```bash
python daily_update.py
```

这会创建：
- `docs/data/regime_data.json` - 包含当前regime和历史数据的JSON文件

**预期输出**：
```
==================================================
🔄 Updating Dashboard Data (Local Test Mode)
==================================================

1. Loading historical data...
   Data range: 2018-XX-XX to 2024-XX-XX

2. Loading model...
   ✓ Model loaded

3. Calculating features for latest date...
   Date: 2024-XX-XX
   BTC Price: $XX,XXX.XX
   Volatility: X.XXXX
   F&G Index: X.XX

4. Predicting regime...
   🔴 Regime: Fear  (或 🟢 Greed)
   📊 Confidence: XX.X%

5. Getting recent history...
   ✓ Loaded 30 days (30d window)
   ✓ Loaded 90 days (90d window)

6. Calculating period statistics...
   Week:  Fear XX% | Greed XX%
   Month: Fear XX% | Greed XX%

7. Saving to JSON...
   ✓ Saved to ../docs/data/regime_data.json

✅ Dashboard data updated successfully!

Current Regime: 🔴 Fear (XX.X% confidence)
BTC Price: $XX,XXX.XX

You can now open docs/index.html in your browser
```

---

## 📋 步骤3：打开网页查看

### 方法1：直接打开HTML文件

```bash
# macOS
open ../docs/index.html

# Linux
xdg-open ../docs/index.html

# Windows
start ../docs/index.html
```

### 方法2：使用Python简单HTTP服务器（推荐）

```bash
cd ../docs
python -m http.server 8000
```

然后在浏览器打开：`http://localhost:8000`

**为什么推荐方法2？**
- 避免浏览器CORS限制（加载JSON文件时）
- 更接近真实部署环境

---

## 🎨 你应该看到什么

### 页面顶部：当前Regime
- **大圆点**：🔴（Fear）或 🟢（Greed）
- **Regime名称**：FEAR 或 GREED（大字体）
- **置信度**：例如 "78.5% confidence"

### 指标卡片
- **BTC Price**: 当前BTC价格
- **F&G Index**: Fear & Greed指数（0-100）
- **Volatility (7d)**: 7日波动率
- **Market Breadth**: 多少%的币种在50日均线上方

### 周期统计
- **This Week**: 本周Fear/Greed百分比，切换次数
- **This Month**: 本月统计
- **This Quarter**: 本季度统计

### 30日时间线图表
- 折线图显示BTC价格
- 点的颜色表示regime（红=Fear，绿=Greed）
- 鼠标悬停可查看详细信息

---

## 🔍 调试技巧

### 如果模型训练失败

检查数据文件是否存在：
```bash
ls -lh ../data/processed/full_market_matrix.csv
```

### 如果JSON生成失败

确保模型文件存在：
```bash
ls -lh ../models/
```

应该看到：
- `kmeans_model.pkl`
- `scaler.pkl`
- `feature_names.txt`

### 如果网页显示"Error Loading Data"

打开浏览器开发者工具（F12），查看Console错误信息。

常见问题：
- CORS错误 → 使用Python HTTP服务器
- JSON not found → 确认`docs/data/regime_data.json`存在
- Invalid JSON → 检查JSON文件格式

---

## 📂 完整文件结构

训练完成后，你的项目应该是这样的：

```
MarketFearRegimeIdentification/
├── models/                      ← 新创建
│   ├── kmeans_model.pkl         ← 训练后生成
│   ├── scaler.pkl               ← 训练后生成
│   └── feature_names.txt        ← 训练后生成
├── scripts/                     ← 新创建
│   ├── train_model.py           ← 你已创建
│   └── daily_update.py          ← 你已创建
├── docs/                        ← 新创建
│   ├── index.html               ← 你已创建
│   ├── css/
│   │   └── style.css            ← 你已创建
│   ├── js/
│   │   └── main.js              ← 你已创建
│   └── data/
│       └── regime_data.json     ← 运行daily_update.py后生成
├── notebooks/                   ← 已有
├── data/                        ← 已有
│   └── processed/
│       ├── full_market_matrix.csv           ← 已有
│       ├── regime_labels.csv                ← 已有
│       └── regime_labels_new.csv            ← 训练后生成
└── [其他文件...]
```

---

## ✅ 成功标志

如果一切顺利，你应该：

1. ✅ 在 `models/` 文件夹看到3个文件
2. ✅ 在 `docs/data/` 看到 `regime_data.json`
3. ✅ 在浏览器看到漂亮的dashboard
4. ✅ dashboard显示实际的数据（不是"Loading..."或"--"）

---

## 🎯 下一步

本地测试成功后，你可以：

1. **调整样式**：修改 `docs/css/style.css`
2. **修改布局**：编辑 `docs/index.html`
3. **添加功能**：扩展 `docs/js/main.js`
4. **准备部署**：配置GitHub Actions（下一步骤）

---

## ❓ 遇到问题？

如果有任何错误，请：
1. 检查上面的"调试技巧"部分
2. 查看终端的完整错误信息
3. 确认所有依赖已安装（pandas, numpy, scikit-learn）
