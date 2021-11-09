from enum import Enum


class commitStatusIcons(Enum):
    success = u'\U0001F7E2'   # green circle
    failed = u'\U0001F534'   # red circle
    pending = u'\U0001F7E0'   # yellow circle


commit_status_to_icon_map = {
    'success': commitStatusIcons.success.value,
    'failed': commitStatusIcons.failed.value,
    'pending': commitStatusIcons.pending.value
}


class mergeStatusIcons(Enum):
    queued = u'\U000023F3'     # hourglass
    merged = u'\U00002705'     # check box
    blocked = u'\U0001F504'    # refresh
    cancelled = u'\U000023F9'  # stop button


merge_status_to_icon_map = {
    'queued': mergeStatusIcons.queued.value,
    'merged': mergeStatusIcons.merged.value,
    'blocked': mergeStatusIcons.blocked.value,
    'cancelled': mergeStatusIcons.cancelled.value
}