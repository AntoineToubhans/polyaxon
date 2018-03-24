class OperationStatus(object):
    CREATED = 'created'
    SCHEDULED = 'scheduled'
    STARTED = 'started'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    STOPPED = 'stopped'
    SKIPPED = 'skipped'
    RETRYING = 'retrying'

    VALUES = [CREATED, STARTED, SCHEDULED, RUNNING, SUCCESS, FAILED, STOPPED, SKIPPED, RETRYING]
    CHOICES = (
        (CREATED, CREATED),
        (SCHEDULED, SCHEDULED),
        (STARTED, STARTED),
        (RUNNING, RUNNING),
        (SUCCESS, SUCCESS),
        (FAILED, FAILED),
        (STOPPED, STOPPED),
        (SKIPPED, SKIPPED),
        (RETRYING, RETRYING)
    )

    DONE_STATUS = [SUCCESS, FAILED, STOPPED, SKIPPED]


class TriggerRule(object):
    ALL_SUCCESS = 'all_success'
    ALL_FAILED = 'all_failed'
    ALL_DONE = 'all_done'
    ONE_SUCCESS = 'one_success'
    ONE_FAILED = 'one_failed'
    ONE_DONE = 'one_done'

    VALUES = [ALL_SUCCESS, ALL_FAILED, ALL_DONE, ONE_SUCCESS, ONE_FAILED, ONE_DONE]
    CHOICES = (
        (ALL_SUCCESS, ALL_SUCCESS),
        (ALL_FAILED, ALL_FAILED),
        (ALL_DONE, ALL_DONE),
        (ONE_SUCCESS, ONE_SUCCESS),
        (ONE_FAILED, ONE_FAILED),
        (ONE_DONE, ONE_DONE),
    )
