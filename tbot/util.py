from typing import List, Tuple
import datetime

from github import Github
import telegram as tg
from telegram import Update
from telegram.ext import CallbackContext

from tbot.credentials import bot_token, chat_id, github_token, target_repos
from tbot.symbols import commit_status_to_icon_map, merge_status_to_icon_map

TOKEN = bot_token
gmt_3 = datetime.timezone(datetime.timedelta(hours=3))

last_message = {}
merge_order = {}


def get_pull_requests(target_names: List[str]):
    """ Fetch pull requests from the parent repositories """
    ghub = Github(github_token)
    test = [repo for repo in ghub.get_user().get_repos()]
    user_repos = [repo for repo in ghub.get_user().get_repos() if repo.name in target_names]
    parent_repos = set([repo.parent if repo.parent else repo for repo in user_repos])

    return {repo.name: repo.get_pulls(state='all')[0:100] for repo in parent_repos}


def construct_plan(pr_info):
    """
    Construct a new merge plan.
    Updates entries in current plan if they exist or adds new ones if they don't.
    """

    new_plan = {}

    for repo_name, pull_requests in pr_info.items():

        # Take relevant segment from current plan for comparing
        # plan_requests = new_plan.get(repo_name, {})
        # Filter open requests and requests that were previously present in the plan
        test = [pr for pr in pull_requests]
        valid_requests = [pr for pr in pull_requests if (pr.state == 'open')
                          or (pr.merged_at and pr.merged_at.date() == datetime.date.today())]
        # Filter requests queued for merging
        request_queue = [pr for pr in valid_requests if any(label.name == 'to-be-merged' for label in pr.labels)]

        repo_plan = {}
        for pull_request in request_queue:
            pr_status = {
                'title': pull_request.title,
                'number': pull_request.number,
                'state': pull_request.state,
                'mergeable': pull_request.mergeable,
                'merged': pull_request.is_merged(),
                'url': pull_request.html_url
            }

            last_commit = pull_request.get_commits().reversed[0]
            pr_status['commit_status'] = get_commit_status(last_commit)

            repo_plan[pull_request.id] = pr_status

        new_plan[repo_name] = repo_plan

    return new_plan


def get_commit_status(commit) -> str:
    raw_status = commit.get_combined_status().state
    if raw_status in ['error', 'failure']:
        return 'failed'
    return raw_status


def get_status_icons(pull_request: dict) -> Tuple[str, str]:
    merge_status = 'queued'
    if pull_request['state'] == 'closed' and not pull_request['merged']:
        merge_status = 'cancelled'
    elif pull_request['state'] == 'closed' and pull_request['merged']:
        merge_status = 'merged'
    elif not pull_request['mergeable']:
        merge_status = 'blocked'

    merge_icon = merge_status_to_icon_map[merge_status]
    check_icon = commit_status_to_icon_map[pull_request['commit_status']]

    return merge_icon, check_icon


def format_plan(plan):
    result = prepare_for_markdown(f'План мержей на {datetime.date.today()}.\n')

    for repo_name, pull_requests in plan.items():
        result += prepare_for_markdown(f'\n{repo_name}:\n')

        # First, place ordered PR's
        global merge_order
        if merge_order.get(repo_name):
            for number in merge_order[repo_name]:
                for pr_name, pr in pull_requests.items():
                    if pr['number'] == number:
                        merge_status, check_status = get_status_icons(pr)

                        buffer = prepare_for_markdown('{} {} {}'.format(merge_status, check_status, pr['title']))
                        buffer += '\\([\\#{}]({})\\)\n'.format(pr['number'], pr['url'])
                        result += buffer

                        pull_requests.pop(pr_name)
                        break

        # process remaining requests
        for _, pr in pull_requests.items():
            merge_status, check_status = get_status_icons(pr)

            buffer = prepare_for_markdown('{} {} {}'.format(merge_status, check_status, pr['title']))
            buffer += '\\([\\#{}]({})\\)\n'.format(pr['number'], pr['url'])
            result += buffer

    return result


def prepare_for_markdown(line: str) -> str:
    result = line
    markdown_reserved = ['.', '-', '(', ')', '[', ']', '#', '_']
    for symbol in markdown_reserved:
        result = result.replace(symbol, f'\\{symbol}')

    return result


def get_plan():
    pr_info = get_pull_requests(target_repos)
    plan = construct_plan(pr_info)

    return format_plan(plan)


def callback_post(_: Update, __: CallbackContext):
    post_plan()


def job_post(_: Update):
    post_plan()


def post_plan():
    bot = tg.Bot(token=TOKEN)
    plan = get_plan()

    global last_message
    if last_message:
        bot.unpin_chat_message(chat_id=chat_id, message_id=last_message['message_id'])
    last_message = bot.sendMessage(chat_id=chat_id, text=plan, parse_mode=tg.constants.PARSEMODE_MARKDOWN_V2)
    bot.pin_chat_message(chat_id=chat_id, message_id=last_message['message_id'])


def callback_update(_: Update, __: CallbackContext):
    update_plan()


def job_update(_):
    update_plan()


def update_plan():
    bot = tg.Bot(token=TOKEN)
    plan = get_plan()

    current_time = datetime.datetime.now(tz=gmt_3).time()
    # if datetime.time(23, 0, 0, tzinfo=gmt_3) <= current_time <= datetime.time(11, 30, 0, tzinfo=gmt_3):
    global last_message
    bot.editMessageText(chat_id=chat_id, message_id=last_message['message_id'], text=plan,
                        parse_mode=tg.constants.PARSEMODE_MARKDOWN_V2)


def callback_reorder(_: Update, context: CallbackContext):
    reorder_merges(context)


def job_reorder(context: CallbackContext):
    reorder_merges(context)


def reorder_merges(context: CallbackContext):
    repo_name, pr_numbers = context.args[0], [int(num) for num in context.args[1:]]

    global merge_order
    merge_order[repo_name] = pr_numbers
    update_plan()