## Outline of The First Version of The Library

### **Data structures:**
* **OHLCV Data:** OHLCV class to run backtest on
* **Trade History:** Trade history class that supports visualization and metrics to be run on it
### **Backtest:**
* Requires a class that implements Trader "interface" i.e. defines 2 methods: entry and monitorand OHLCV object
### **Visualization:**
* (To be updated) For now, something like this:
![Gif](https://media1.giphy.com/media/SV1u3WJjoHMTsrAIB0/giphy.gif)
[Source](https://towardsdatascience.com/introduction-to-interactive-time-series-visualizations-with-plotly-in-python-d3219eb7a7af)
### **Metrics:**
* Takes in Trade History object
* Trades Won Ratio, [Sharpe Ratio](https://www.investopedia.com/terms/s/sharperatio.asp), [Sortino Ratio](https://www.investopedia.com/terms/s/sortinoratio.asp), [Max Drawdown](https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp), [Max Drawdown Duration](https://en.wikipedia.org/wiki/Drawdown_(economics)#Trading_definitions), etc.
