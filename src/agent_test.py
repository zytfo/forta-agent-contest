from parser import update_pools_data
from apscheduler.schedulers.background import BackgroundScheduler
import time



def main():
    update_pools_data()
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_pools_data, 'interval', hours=24)
    scheduler.start()
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        # scheduler.shutdown()
        pass