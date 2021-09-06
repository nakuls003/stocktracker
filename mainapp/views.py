import time
import queue
from threading import Thread
from django.http import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import *


def stock_picker(request):
    stocks = tickers_nifty50()
    return render(request, 'mainapp/stock_picker.html', {'stocks': stocks})


def stock_tracker(request):
    stocks_picked = request.GET.getlist('stockpicker')
    available_stocks = set(tickers_nifty50())
    data = {}
    if set(stocks_picked) - available_stocks:
        return HttpResponse('Error, invalid stock picked')

    start = time.time()
    q = queue.Queue()
    thread_list = []
    for i in range(len(stocks_picked)):
        thread = Thread(target=lambda que, stock: que.put({stock: get_quote_table(stock)}), args=(q, stocks_picked[i]))
        thread.start()
        thread_list.append(thread)

    for thread in thread_list:
        thread.join()

    while not q.empty():
        result = q.get()
        data.update(result)
    print('time taken: {}'.format(time.time() - start))
    # for stock in stocks_picked:
    #     data[stock] = get_quote_table(stock)
    print(data)
    return render(request, 'mainapp/stock_tracker.html', {'data': data})
