import pandas as pd
import numpy as np
from tqdm.notebook import tqdm


class Position:
    """
    Position class to store data about the position the algorithm is currently in.
    """

    def __init__(self, position_type, entry_time, entry_price, allocation=1):
        """
        Initializes a position with type (Long or Short) and keeps track of the time and price at which we entered.
        Also, keeps track of allocation which is a fraction of total principal that we allocation to the position.
        @param position_type: Long or Short position. Trade PNL will be based on this.
        @param entry_time: Time at which the algorithm enters the position.
        @param entry_price: Price at which the algorithm enters the position.
        @param allocation: Fraction of total principal the algorithm allocates to the position. Cannot be > 1.
        """
        self.position_type = position_type
        if allocation > 1:
            self.allocation = 1
        else:
            self.allocation = allocation
        self.allocate_history = [(entry_time, entry_price, self.allocation)]
        self.entry_time = entry_time

    def add_to_position(self, time, price, allocation):
        """
        Allocates more fraction of total principal to an existing position at a given price and keeps track of the time.
        @param time: Time at which the algorithm adds to the position.
        @param price: Price at which the algorithm adds to the position
        @param allocation: Fraction of total principal to add. Cannot be > 1 when summed with existing allocation.
        """
        allocation = np.round(allocation, 2)
        if self.allocation != 1:
            # print('Added')
            if self.allocation + allocation <= 1:
                self.allocate_history.append((time, price, allocation))
                self.allocation += allocation
            else:
                self.allocate_history.append((time, price, 1 - self.allocation))
                self.allocation += (1 - self.allocation)
        # else:
        #    print("Already allocated 100%!!!")


class Backtester:
    """
    Backtester class implements the backend required to backtest most algorithms
    """

    def __init__(self, data, trade_amount=100, lookback=8):
        """
        Initializes the backtester with OHLCV (and other features) data and some optional arguments
        @param data: OHLCV+ data to backtest on
        @param trade_amount: Starting amount to trade with
        @param lookback: Number of candles to look back on. Skips the first lookback number of candles as well.
        """
        self.data = data
        self.lookback = lookback
        self.trade_amount = trade_amount
        self.trade_history = pd.DataFrame(
            columns=['Trade_Type', 'Allocation_Count', 'Entry_Timestamp', 'Exit_Timestamp', 'Allocation_History',
                     'Total_Allocation', 'Exit_Price', 'Trade_PNL', 'Aggregate_PNL', 'Stopped', 'Trade_Duration',
                     'Trade_amount'])
        self.in_a_position = False
        self.position = None
        self.allocation_count = 0
        self.transaction_cost = 0
        self.leverage = 1

    def enter_position(self, position_type, entry_time, entry_price, index, allocation=1):
        """
        Enter a position based on given type, time, price, and allocation.
        @param position_type: Long or Short position Type. Affects PNL accordingly.
        @param entry_time: Time at which the algorithm enters the trade.
        @param entry_price: Price.
        @param index: Index to allow for more customization in the future.
        @param allocation: Fraction of total principal the algorithm allocates to the position.
        """
        self.allocation_count += 1
        if not self.in_a_position:
            self.position = Position(position_type, entry_time, entry_price, allocation)
            self.in_a_position = True
        else:
            print('Already in a position')

    def trade_pnl(self, index):
        """
        Gets PNL based on the allocated fraction of the total principal. PNL based on the amount risked.
        @param index: the candle for which to get the trade PNL for.
        @return: PNL for the current trade based on allocated fraction.
        """
        exit_price = self.data.Close[index]
        total = 0
        if self.position.position_type == 'Long':
            for time_allocation in self.position.allocate_history:
                total += time_allocation[2] * (1 + (exit_price - time_allocation[1]) / time_allocation[1])
                # print('Long',time_allocation[2],exit_price,time_allocation[1])
        else:
            for time_allocation in self.position.allocate_history:
                total += time_allocation[2] * (1 - (exit_price - time_allocation[1]) / time_allocation[1])
                # print('Short',time_allocation[2],exit_price,time_allocation[1])
        pnl = (total - self.position.allocation) / self.position.allocation
        pnl = pnl - self.transaction_cost
        return pnl

    def aggregate_pnl(self, index):
        """
        Gets PNL based on total principal. PNL based on the total amount the algorithm has.
        @param index: the candle for which to get the aggregate PNL for.
        @return: PNL for the current trade based on total amount the algorithm has.
        """
        exit_price = self.data.Close[index]
        total = 0
        if self.position.position_type == 'Long':
            for time_allocation in self.position.allocate_history:
                total += time_allocation[2] * (1 + (exit_price - time_allocation[1]) / time_allocation[1])
                # print(time_allocation[2] * (1 + (exit_price - time_allocation[1])/time_allocation[1]))
                # print(time_allocation[1])
        else:
            for time_allocation in self.position.allocate_history:
                total += time_allocation[2] * (1 - (exit_price - time_allocation[1]) / time_allocation[1])
        pnl = (total - self.position.allocation)
        pnl = (pnl - self.transaction_cost * self.position.allocation) * self.leverage
        return pnl

    def exit_position(self, index, stopped=False):
        """
        Exits current position and resets any parameters used for the Position.
        @param index: Candle on which we exit the trade
        @param stopped: Flag for whether the current trade reached a stop loss and got stopped
        """
        current_pnl = self.trade_pnl(index)
        # print('---Exiting---', self.aggregate_pnl(index))
        # if current_pnl > 0:
        #     self.trade_won += 1
        # else:
        #     self.trade_lost += 1
        self.trade_amount = self.trade_amount * (1 + self.aggregate_pnl(index))
        self.trade_history = self.trade_history.append(
            {'Trade_Type': self.position.position_type, 'Allocation_Count': self.allocation_count,
             'Entry_Timestamp': self.position.entry_time, 'Allocation_History': self.position.allocate_history,
             'Total_Allocation': self.position.allocation, 'Exit_Timestamp': self.data.index[index],
             'Exit_Price': self.data.Close[index], 'Trade_PNL': current_pnl, 'Aggregate_PNL': self.aggregate_pnl(index),
             'Stopped': stopped, 'Trade_Duration': (self.data.index[index]
                                                    - self.position.entry_time).total_seconds() / 60.0,
             'Trade_amount': self.trade_amount},
            ignore_index=True)

        self.reset_trade_parameters()

    def reset_trade_parameters(self):
        """
        Resets any parameter that needs to be reset for the next trade
        @return:
        """
        self.allocation_count = 0
        self.position = None
        self.in_a_position = False

    def add_to_position(self, index, time, price, allocate):
        """
        Adds a fraction of total principal at a given price.
        @param index: Index to allow for more customization in the future.
        @param time: Time at which the algorithm adds to the position
        @param price: Price at which the algorithm adds to the position
        @param allocate: Fraction of principal to allocate.
        """
        self.position.add_to_position(time, price, allocate)

    def backtest(self, entry, monitor):
        """
        Starts the backtest taking a entry and monitor function from the user
        @param entry: User-defined function (entry(self,i)) that returns 0 if the algorithm should not enter a trade
        and anywhere from -1 to 1 (except 0) to allocate that fraction of principal to enter the trade.
        -0.5 short sells using 50% of principal similarly 0.5 buys long using 50% of the trade amount.
        @param monitor: User-defined function (monitor(self,i)) that returns 0 if the algorithm should wait anywhere
        from -1 to 1 (except 0) to exit or at to the position of the trade.
        -0.5 exits with 0.5 from the total allocation amount. -0.5 exits the whole position if total allocation is < 0.5
        whereas 0.5 adds to the position by adding 50% of the total amount at the current price.
        @return: Trade History DataFrame that logs the the trades that the algorithm makes.
        """
        for i in tqdm(range(self.lookback, len(self.data))):
            self.clear_trade_history()
            if self.in_a_position:
                if monitor(self, i):
                    self.exit_position(i)
            else:
                entry_allocation = entry(self, i)
                if entry_allocation:
                    if entry_allocation < 0:
                        self.enter_position('Short', self.data.index[i], self.data.Close[i], i, -1 * entry_allocation)
                    elif entry_allocation > 0:
                        self.enter_position('Long', self.data.index[i], self.data.Close[i], i, entry_allocation)
        return self.trade_history

    def clear_trade_history(self):
        """
        Clears trade history to start a new backtest
        """
        self.trade_history = self.trade_history = pd.DataFrame(
            columns=['Trade_Type', 'Allocation_Count', 'Entry_Timestamp', 'Exit_Timestamp', 'Allocation_History',
                     'Total_Allocation', 'Exit_Price', 'Trade_PNL', 'Aggregate_PNL', 'Stopped', 'Trade_Duration',
                     'Trade_amount'])
