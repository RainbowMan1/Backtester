import pandas as pd
import numpy as np
from tqdm.notebook import tqdm


class Position:
    def __init__(self, position_type, entry_time, entry_price, allocation=1):
        self.position_type = position_type
        if allocation > 1:
            self.allocation = 1
        else:
            self.allocation = allocation
        self.allocate_history = [(entry_time, entry_price, self.allocation)]
        self.entry_time = entry_time

    def add_to_position(self, time, price, allocation):
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

    def __init__(self, data, trade_amount=100, lookback=8):
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
        self.allocation_count += 1
        if not self.in_a_position:
            self.position = Position(position_type, entry_time, entry_price, allocation)
            self.in_a_position = True
        else:
            print('Already in a position')

    def trade_pnl(self, index):
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

        self.position = None
        self.in_a_position = False
        self.reset_trade_parameter()

    def reset_trade_parameter(self):
        self.allocation_count = 0

    def add_to_position(self, index, time, price, allocate):
        self.position.add_to_position(time, price, allocate)

    def backtest(self, entry, monitor):
        for i in tqdm(range(self.lookback, len(self.data))):
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
