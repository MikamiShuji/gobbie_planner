import logging
import datetime

from telegram.ext import Updater, CommandHandler
from tbot.credentials import bot_token

from tbot.util import job_post, job_update, callback_post,callback_update, callback_reorder

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    updater = Updater(token=bot_token, use_context=True)
    queue = updater.job_queue

    queue.run_daily(job_post, days=(0, 1, 2, 3, 4),
                    time=datetime.time(hour=11, minute=30, second=00))
    queue.run_repeating(job_update, interval=datetime.timedelta(minutes=10))

    updater.dispatcher.add_handler(CommandHandler("rebuild", callback_post))
    updater.dispatcher.add_handler(CommandHandler("update", callback_update))
    updater.dispatcher.add_handler(CommandHandler("reorder", callback_reorder))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
