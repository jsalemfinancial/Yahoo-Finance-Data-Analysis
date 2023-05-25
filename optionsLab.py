import yfinance as yf
import datetime
import pandas as pd
from scipy.stats import norm
import math

def bsNewtonItteration(marketValue, optionType, S, K, T, r):
    MAX_ITERATIONS = 100
    PRECISION = 0.00001

    sigmaGuess = [0.5, 0.75, 0.25, 1.25] # initial guesses. We test 3 spread out guesses.
    # In case one yields a diverging or converges to 0 (leading to division by zero or overflow), we test another.

    for guess in sigmaGuess:
        diff = 1e10
        sigma = guess

        for i in range(0, MAX_ITERATIONS):
            if (sigma > guess):
                break

            price = bsOptionPrice(optionType, S, K, T, r, sigma)
            vega = findVega(S, K, T, r, sigma)

            prevDiff = diff
            diff = marketValue - price

            if (abs(diff) < PRECISION):
                return sigma
            elif (vega == 0):
                break

            sigma = sigma + diff/vega

    return 0

def bsOptionPrice(optionType,S,K,T,r,v):
    d1 = (math.log(S/K)+(r+(v*v)/2)*T)/(v*math.sqrt(T))
    d2 = d1-v*math.sqrt(T)

    if optionType == 'c':
        price = S*norm.cdf(d1)-K*math.exp(-r*(T))*norm.cdf(d2)
    else: # this is the put derived from put-call parity.
        price = K*math.exp(-r*(T))*norm.cdf(-d2)-S*norm.cdf(-d1)

    return price
    
def findVega(S,K,T,r,v):
    d1 = (math.log(S/K)+(r+(v*v)/2)*T)/(v*math.sqrt(T))

    return S * math.sqrt(T)*norm.pdf(d1)

def historicVolatility(prices):

    logPrices = []

    for row in prices.itertuples():
        logPrices.append(row.Close)

    logPrices2 = logPrices.copy()
    logPrices = logPrices[1:len(logPrices)]

    logPrices = [math.log((x/y))*math.log((x/y)) for (x,y) in zip(logPrices, logPrices2)]
    
    return [math.sqrt((1/(len(logPrices) - 1))*sum(logPrices)), math.sqrt((1/(len(logPrices) - 1))*sum(logPrices))*math.sqrt(252)]

def betaAndCorrCoeff(prices, benchmarkPrices):
    logPrices = []
    logBenchmarkPrices = []

    for row in prices.itertuples():
        logPrices.append(row.Close)
        
    for row in benchmarkPrices.itertuples():
        logBenchmarkPrices.append(row.Close)

    logPrices2 = logPrices.copy()
    logPrices = logPrices[1:len(logPrices)]

    logBenchmarkPrices2 = logBenchmarkPrices.copy()
    logBenchmarkPrices = logBenchmarkPrices[1:len(logBenchmarkPrices)]

    logPricesReturn = [math.log((x/y)) for (x,y) in zip(logPrices, logPrices2)]
    logBenchmarkPricesReturn = [math.log((x/y)) for (x,y) in zip(logBenchmarkPrices, logBenchmarkPrices2)]

    covCorrDataframe = pd.DataFrame({"Ticker": logPricesReturn, "Benchmark": logBenchmarkPricesReturn})

    beta = covCorrDataframe.cov().iloc[1]["Ticker"]/covCorrDataframe.cov().iloc[0]["Ticker"]
    returnCorr = covCorrDataframe.corr(method="pearson").iloc[1]["Ticker"]

    return [beta, returnCorr]

def solveImpVolCallPut(calls, puts, spotPrice, expirations, rate):
    today = datetime.datetime.today()

    for i in range(0, len(expirations)):
        expiryTime = (datetime.datetime.strptime(expirations[i], "%Y-%m-%d").date() - today.date()).days / 365 # this is in years (as everything else is annualized), thus we divide by 365.

        callIVs = []
        putIVs = []

        for row in calls[i].itertuples():
            callIVs.append(bsNewtonItteration(row.lastPrice, 'c', spotPrice, row.strike, expiryTime, rate))

        for row in puts[i].itertuples():
            putIVs.append(bsNewtonItteration(row.lastPrice, 'p', spotPrice, row.strike, expiryTime, rate))

        calls[i]["IV"] = callIVs
        puts[i]["IV"] = putIVs

        print("\n", expirations[i], "\n", "Calls- \n", calls[i], "\n", "Puts- \n", puts[i])

    return

def main():
    while (True):
        try:
            symb = str(input("Enter Ticker: "))
            ticker = yf.Ticker(symb)
            info = ticker.info
        except:
            print("Ticker not found. \n")
            continue
        else:
            try:
                benchmark = str(input("Enter Market Benchmark Ticker: "))
                benchmarkTicker = yf.Ticker(benchmark)
                info = benchmarkTicker.info
            except:
                print("Benchmark Ticker not found. \n")
                continue
            else:
                break

    optionsTablesBool= input("Options Tables (y/n)? ")

    if (optionsTablesBool == "y"):
        riskfreeRate = float(input("Enter Risk-free Rate: "))

        expiration = ticker.options

        calls = []
        puts = []

        for date in expiration: # fetch option chain dataframes and into arrays
            optionChain = ticker.option_chain(date)

            callOpt = optionChain.calls.drop(columns= ["lastTradeDate", "impliedVolatility", "contractSymbol", "contractSize", "bid", "ask", "percentChange", "change"])
            putOpt = optionChain.puts.drop(columns= ["lastTradeDate", "impliedVolatility", "contractSymbol", "contractSize", "bid", "ask", "percentChange", "change"])

            calls.append(callOpt)
            puts.append(putOpt)
            
        spotPrice = ticker.info['regularMarketPrice']

        discountTime = 0 # optional parameter for pricing model, the number days before expiration. Used in the discount factor.
        # the discount factor used is e^(-r(T-t)), which comes from a coupon bond (typically the nearest annualized treasury bill rate) with risk-free rate r.

        solveImpVolCallPut(calls, puts, spotPrice, expiration, riskfreeRate)

    print("\n")
    
    historicalPrice = ticker.history(period="1mo", interval="1d") # fetch 1 month daily bar data
    historicalPrice.drop(columns= ["Volume", "Dividends", "Stock Splits"])

    benchmarkHistoricalPrice = benchmarkTicker.history(period="1mo", interval="1d")
    benchmarkHistoricalPrice.drop(columns= ["Volume", "Dividends", "Stock Splits"])

    histVolatility = historicVolatility(historicalPrice)

    print("Daily Historical Volatility: ", "%" + str(round(histVolatility[0]*100, 4)))
    print("Annualized Historical Volatility: ", "%" + str(round(histVolatility[1]*100, 4)), "\n")

    betaAndCorr = betaAndCorrCoeff(historicalPrice, benchmarkHistoricalPrice)

    print("Beta Value: ", "%" + str(round(betaAndCorr[0]*100, 4)))
    print("Returns Pearson Correlation: ", str(round(betaAndCorr[1]*100, 4)), "\n")

if __name__ == "__main__":
    main()