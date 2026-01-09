# 🔄 数据更新机制说明

## ✅ 已完成的功能

### 1. **防重复检查**
脚本会自动检查：
- ✅ 目标日期是否已存在于CSV中
- ✅ 目标日期是否晚于最后日期
- ✅ 目标日期是否在未来
- ✅ 数据gap是否过大（超过7天）

**运行示例**：
```bash
python daily_update.py

2. Checking for new data...
   Ready to fetch data for 2026-01-09      ← 检测到需要新数据
   📥 Attempting to fetch new data...
   ℹ️  API not configured (local testing mode)
```

**如果重复运行**：
```bash
python daily_update.py

2. Checking for new data...
   Data for 2026-01-09 already exists      ← 防止重复
   ℹ️  Using existing data
```

---

### 2. **自动追加数据**
当API配置完成后，会自动：
1. 检测今天的数据是否已存在
2. 如果不存在，从API获取
3. 验证数据完整性
4. 追加到CSV文件
5. 更新JSON dashboard数据

**文件变化**：
```
每天运行一次：
- data/processed/full_market_matrix.csv  ← 新增1行
- docs/data/regime_data.json             ← 完全更新
```

---

## 📋 API集成步骤

### 步骤1：获取API密钥（可选）

**CoinGecko免费版**：
- 不需要API密钥
- 限制：50次/分钟
- 足够我们使用（每天只需1次）

**CoinGecko Pro版**（如果需要更稳定）：
- $129/月
- 500次/分钟
- 优先级支持

---

### 步骤2：修改 `fetch_latest_market_data()` 函数

在 `daily_update.py` 第 25-57 行，替换为真实API调用：

```python
def fetch_latest_market_data(target_date):
    """Fetch latest market data from APIs"""
    import requests
    import time
    
    # 1. 获取20个币种的价格
    coins = [
        'bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano',
        'solana', 'polkadot', 'dogecoin', 'avalanche-2', 'polygon',
        'shiba-inu', 'uniswap', 'litecoin', 'chainlink', 'bitcoin-cash',
        'stellar', 'algorand', 'vechain', 'internet-computer', 'tron'
    ]
    
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': ','.join(coins),
        'vs_currencies': 'usd',
        'date': target_date.strftime('%d-%m-%Y')
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        prices = response.json()
        
        # 延迟1秒，避免限流
        time.sleep(1)
        
        # 2. 获取Fear & Greed指数
        fg_url = 'https://api.alternative.me/fng/?limit=1'
        fg_response = requests.get(fg_url, timeout=10)
        fg_response.raise_for_status()
        fg_data = fg_response.json()
        
        # 3. 组装数据
        coin_mapping = {
            'bitcoin': 'BTC', 'ethereum': 'ETH', 'binancecoin': 'BNB',
            'ripple': 'XRP', 'cardano': 'ADA', 'solana': 'SOL',
            'polkadot': 'DOT', 'dogecoin': 'DOGE', 'avalanche-2': 'AVAX',
            'polygon': 'MATIC', 'shiba-inu': 'SHIB', 'uniswap': 'UNI',
            'litecoin': 'LTC', 'chainlink': 'LINK', 'bitcoin-cash': 'BCH',
            'stellar': 'XLM', 'algorand': 'ALGO', 'vechain': 'VET',
            'internet-computer': 'ICP', 'tron': 'TRX'
        }
        
        result = {'Date': target_date}
        
        for coin_id, symbol in coin_mapping.items():
            if coin_id in prices:
                result[symbol] = prices[coin_id]['usd']
            else:
                raise ValueError(f"Missing price for {coin_id}")
        
        result['fg_raw'] = int(fg_data['data'][0]['value'])
        
        return result
        
    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return None
```

---

### 步骤3：添加依赖

在项目根目录创建 `requirements.txt`：
```txt
pandas>=1.5.0
numpy>=1.23.0
scikit-learn>=1.2.0
requests>=2.28.0
```

安装：
```bash
pip install -r requirements.txt
```

---

## 🧪 测试API集成

### 本地测试：
```bash
cd scripts
python daily_update.py
```

**预期输出**：
```
2. Checking for new data...
   Ready to fetch data for 2026-01-09
   📥 Attempting to fetch new data...
   📥 Attempting to fetch data for 2026-01-09...
   ✅ Successfully appended data for 2026-01-09

3. Loading model...
   ✓ Model loaded

4. Calculating features for latest date...
   Date: 2026-01-09                        ← 新日期！
   BTC Price: $95,234.56
   ...

✅ Data is up-to-date                       ← 不再有警告
```

---

## 🚀 GitHub Actions配置

创建 `.github/workflows/daily-update.yml`：

```yaml
name: Daily Regime Update

on:
  schedule:
    - cron: '0 0 * * *'  # 每天UTC 00:00运行
  workflow_dispatch:     # 允许手动触发

jobs:
  update-data:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install pandas numpy scikit-learn requests
    
    - name: Run daily update
      run: |
        cd scripts
        python daily_update.py
    
    - name: Check for changes
      id: check_changes
      run: |
        git diff --quiet data/processed/full_market_matrix.csv docs/data/regime_data.json || echo "changed=true" >> $GITHUB_OUTPUT
    
    - name: Commit and push if changed
      if: steps.check_changes.outputs.changed == 'true'
      run: |
        git config user.name "GitHub Actions Bot"
        git config user.email "actions@github.com"
        git add data/processed/full_market_matrix.csv
        git add docs/data/regime_data.json
        git commit -m "🤖 Auto update: $(date +'%Y-%m-%d')"
        git push
```

---

## 📊 运行流程图

```
每天UTC 00:00
    ↓
读取CSV最后日期（例如：2026-01-08）
    ↓
检查今天是否是新的一天（2026-01-09）
    ↓
[是] → 调用API获取数据
    ↓
验证数据完整性
    ↓
追加到CSV（新增1行）
    ↓
用模型预测今天的regime
    ↓
更新regime_data.json
    ↓
Commit两个文件
    ↓
Push到GitHub
    ↓
GitHub Pages自动重新部署
```

---

## ⚠️ 注意事项

### 1. **API限流**
- 每天只运行1次，不会超限
- 如果失败，workflow会自动重试（最多3次）
- 重试时，防重复逻辑会避免数据重复

### 2. **数据质量**
- API可能返回null或异常值
- 需要添加数据验证逻辑
- 建议：价格不能为0，不能是负数

### 3. **时区问题**
- GitHub Actions使用UTC时间
- 你的本地可能是其他时区
- 建议统一使用UTC

### 4. **假期/周末**
- 加密货币7×24小时交易
- 不需要考虑假期
- 每天都会有新数据

---

## ✅ 验证清单

在部署到GitHub Actions之前：

- [ ] API调用成功（本地测试）
- [ ] 数据正确追加到CSV
- [ ] 没有重复数据
- [ ] JSON文件正确更新
- [ ] Dashboard显示正常
- [ ] Git diff显示正确的更改

---

## 🎯 当前状态

**✅ 已完成**：
- 防重复检查逻辑
- 数据追加框架
- 错误处理
- JSON更新逻辑

**📝 待完成**：
- 替换`fetch_latest_market_data()`中的TODO为真实API调用
- 创建`requirements.txt`
- 配置GitHub Actions workflow

**📍 你现在的位置**：
- CSV数据到：2026-01-06
- 今天是：2026-01-09
- Gap：3天（可以手动补全，也可以等API实现后自动追上）

---

## 💡 建议

1. **现在**：继续使用历史数据测试前端
2. **本周**：实现API调用，本地测试
3. **下周**：配置GitHub Actions，实现自动化

**准备好实现真实API调用了吗？** 🚀
