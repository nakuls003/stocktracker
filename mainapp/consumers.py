import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import StockDetail


class StockTrackerConsumer(AsyncWebsocketConsumer):

    @sync_to_async
    def add_or_update_task(self, picked_stocks):
        print("Picked stocks: " + str(picked_stocks))
        task = PeriodicTask.objects.filter(name='load-stocks-data')
        if len(task) > 0:
            task = task.first()
            existing_stocks = json.loads(task.args)[0]
            print("Existing stocks: " + str(existing_stocks))
            for stock in picked_stocks:
                if stock not in existing_stocks:
                    existing_stocks.append(stock)
            task.args = json.dumps([existing_stocks])
            task.save()
        else:
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=10,
                period=IntervalSchedule.SECONDS
            )
            task = PeriodicTask.objects.create(
                name='load-stocks-data',
                interval=schedule,
                task='mainapp.tasks.update_stock_data',
                args=json.dumps([picked_stocks])
            )

    @sync_to_async
    def add_stocks_for_user(self, picked_stocks):
        for stock_name in picked_stocks:
            stock, created = StockDetail.objects.get_or_create(stock_name=stock_name)
            stock.user.add(self.scope['user'])

    async def connect(self):
        self.group_name = 'stock_tracker'

        query_params = parse_qs(self.scope['query_string'].decode())
        picked_stocks = query_params['stockpicker']

        await self.add_or_update_task(picked_stocks)
        await self.add_stocks_for_user(picked_stocks)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    @sync_to_async
    def remove_stocks_for_user(self):
        user = self.scope['user']
        stocks = StockDetail.objects.filter(user__id=user.id)
        stocks_to_remove = set()
        for stock in stocks:
            stock.user.remove(user)
            if stock.user.count() == 0:
                print("remove stock {}".format(stock))
                stocks_to_remove.add(stock.stock_name)

        if stocks_to_remove:
            task = PeriodicTask.objects.filter(name='load-stocks-data').first()
            args = json.loads(task.args)[0]
            currently_tracked_stocks = set(args)
            print("Currently tracked stocks:" + str(currently_tracked_stocks))
            print("Stocks to remove:" + str(stocks_to_remove))
            updated_stock_list = currently_tracked_stocks - stocks_to_remove
            if updated_stock_list:
                print("Updating task as user broke connection")
                print("New updated stock list is " + str(updated_stock_list))
                task.args = json.dumps([list(updated_stock_list)])
                task.save()
            else:
                print("Deleting task as there's no active user online")
                task.delete()

    async def disconnect(self, code):
        await self.remove_stocks_for_user()

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )


    @sync_to_async
    def get_stocks_for_user(self):
        user = self.scope['user']
        picked_stocks = user.stockdetail_set.values_list('stock_name', flat=True)
        return list(picked_stocks)

    async def update_stocks(self, event):
        user = self.scope['user']
        print("pushing stocks for user " + str(user))
        print("Data received: " + str(event['message']))
        picked_stocks = await self.get_stocks_for_user()
        print("picked stocks (inside update_stocks) " + str(picked_stocks))
        stock_data = {stock: event['message'][stock] for stock in picked_stocks}
        await self.send(text_data=json.dumps(stock_data))
