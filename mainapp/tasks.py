from celery import shared_task
from yahoo_fin.stock_info import *
from threading import Thread
import simplejson as json
import queue
import asyncio
from channels.layers import get_channel_layer

@shared_task(bind=True)
def update_stock_data(self, stocks_picked):
    available_stocks = set(tickers_nifty50())
    stocks_picked = list(set(stocks_picked).intersection(available_stocks))
    data = {}

    q = queue.Queue()
    thread_list = []
    for i in range(len(stocks_picked)):
        thread = Thread(target=lambda que, stock: que.put({stock: json.loads(json.dumps(get_quote_table(stock), ignore_nan=True))}),
                        args=(q, stocks_picked[i]))
        thread.start()
        thread_list.append(thread)

    for thread in thread_list:
        thread.join()

    while not q.empty():
        result = q.get()
        data.update(result)

    print(data)

    # send data to channel group
    channel_layer = get_channel_layer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(channel_layer.group_send('stock_tracker',
                                                     {
                                                         'type': 'update_stocks',
                                                         'message': data
                                                     }))
