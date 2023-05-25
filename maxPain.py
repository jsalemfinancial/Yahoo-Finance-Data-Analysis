import yfinance as yf
import pandas as pd

def dictRound(dict, dcm):
    rndDict = {}

    for key, value in dict.items():
        rndDict[key] = round(value, dcm)
    
    return rndDict

def findMaxPain(calls, puts, expiration):
    maxPain = {}

    for date in expiration:
        callDlrVals = {}
        putDlrVals = {}
        painType = "Call Kill"

        for call_strike_opnInt in calls.loc[(calls["expiration"] == date), ["strike", "openInterest", "lastPrice"]].itertuples(index=False):
            callDlrVals[call_strike_opnInt.strike] = call_strike_opnInt.lastPrice*call_strike_opnInt.openInterest

        for put_strike_opnInt in puts.loc[(puts["expiration"] == date), ["strike", "openInterest", "lastPrice"]].itertuples(index=False):
            putDlrVals[put_strike_opnInt.strike] = put_strike_opnInt.lastPrice*put_strike_opnInt.openInterest

        strike_netDlrVals = {key:(callDlrVals.setdefault(key, 0) - putDlrVals.setdefault(key, 0)) for key in set(list(callDlrVals.keys()) + list(putDlrVals.keys()))}
        strike_netDlrVals = dictRound(strike_netDlrVals, 2)

        maxPainKey = max(strike_netDlrVals, key=lambda k: abs(strike_netDlrVals[k]))

        if strike_netDlrVals[maxPainKey] < 0:
            painType = "Put Kill"

        maxPain[date] = [maxPainKey,abs(strike_netDlrVals[maxPainKey]), painType]

    maxPain_dataFrame = pd.DataFrame.from_dict(maxPain, orient="index", columns=["Strike ($)", "Value ($100)", "Pain Type"])

    return maxPain_dataFrame

def main():

    symb = str(input("Enter Ticker: "))
    print("Calculating. . .")

    ticker = yf.Ticker(symb)

    callOpt_dataFrame = pd.DataFrame()
    putOpt_dataFrame = pd.DataFrame()

    expiration = ticker.options

    for date in expiration:
        opt_chain = ticker.option_chain(date)
        callOpt = opt_chain.calls
        putOpt = opt_chain.puts

        callOpt["expiration"] = date
        putOpt["expiration"] = date

        callOpt_dataFrame = callOpt_dataFrame.append(callOpt, ignore_index = True)
        putOpt_dataFrame = putOpt_dataFrame.append(putOpt, ignore_index = True)

    callOpt_dataFrame = callOpt_dataFrame.drop(columns=["lastTradeDate", "impliedVolatility", "contractSymbol", "volume", "percentChange", "bid", "ask", "change"])
    putOpt_dataFrame = putOpt_dataFrame.drop(columns=["lastTradeDate", "impliedVolatility", "contractSymbol", "volume", "percentChange", "bid", "ask", "change"])

    maxPain = findMaxPain(callOpt_dataFrame, putOpt_dataFrame, expiration)

    print(maxPain)    
    input("Press Anything to Exit.")

    return

if __name__ == "__main__":
    main()

