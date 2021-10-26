import textwrap

import pytest

from pubtools.pulplib import Task, InvalidDataException


def test_bad_state():
    """from_data raises if input data has bogus state"""
    with pytest.raises(InvalidDataException):
        Task.from_data({"task_id": "abc", "state": "whatever"})


def test_successful_task():
    """from_data sets attributes appropriately for a successful task"""
    task = Task.from_data({"task_id": "some-task", "state": "finished"})
    assert task == Task(id="some-task", completed=True, succeeded=True)


def test_integer_result():
    """from_data tolerates integer values in 'result' field.

    This test exists because the 'result' field can contain different types
    (e.g. None, integer, dict) based on the type of task which was executed.
    In some cases, we want to parse the dict. The test protects against
    unconditionally assuming we always have a dict.
    """
    task = Task.from_data({"task_id": "some-task", "state": "finished", "result": 123})
    assert task == Task(id="some-task", completed=True, succeeded=True)


def test_failed_task():
    """from_data sets attributes appropriately for a failed task"""
    task = Task.from_data({"task_id": "some-task", "state": "error"})
    assert task == Task(
        id="some-task",
        completed=True,
        succeeded=False,
        error_summary="Pulp task [some-task] failed: <unknown error>",
        error_details="Pulp task [some-task] failed: <unknown error>",
    )


def test_canceled_task():
    """from_data sets attributes appropriately for a canceled task"""
    task = Task.from_data({"task_id": "some-task", "state": "canceled"})
    assert task == Task(
        id="some-task",
        completed=True,
        succeeded=False,
        error_summary="Pulp task [some-task] was canceled",
        error_details="Pulp task [some-task] was canceled",
    )


def test_task_error():
    """from_data sets error-related attributes appropriately"""
    data = {
        "task_id": "failed-task",
        "state": "error",
        "error": {
            "code": "ABC00123",
            "description": "Simulated error",
            "data": {
                "message": "message from data",
                "details": {"errors": ["another message", "and another"]},
            },
        },
        "traceback": textwrap.dedent(
            """
            Traceback (most recent call last):
                File "/usr/lib/python2.7/site-packages/celery/app/trace.py", line 367, in trace_task
                    R = retval = fun(*args, **kwargs)
                File "/home/vagrant/devel/pulp/server/pulp/server/db/querysets.py", line 119, in get_or_404
                    raise pulp_exceptions.MissingResource(**kwargs)
                MissingResource: Missing resource(s): repo_id=zoo, distributor_id=iso_distributor
            """
        ).strip(),
    }
    task = Task.from_data(data)
    assert (
        task.error_summary
        == "Pulp task [failed-task] failed: ABC00123: Simulated error"
    )
    assert (
        task.error_details
        == textwrap.dedent(
            """
            Pulp task [failed-task] failed: ABC00123: Simulated error:
              message from data
              another message
              and another
              Traceback (most recent call last):
                  File "/usr/lib/python2.7/site-packages/celery/app/trace.py", line 367, in trace_task
                      R = retval = fun(*args, **kwargs)
                  File "/home/vagrant/devel/pulp/server/pulp/server/db/querysets.py", line 119, in get_or_404
                      raise pulp_exceptions.MissingResource(**kwargs)
                  MissingResource: Missing resource(s): repo_id=zoo, distributor_id=iso_distributor
            """
        ).strip()
    )


def test_task_repo_id_from_tags():
    """repo_id is initialized from tags where possible"""
    task = Task.from_data(
        {
            "task_id": "some-task",
            "state": "finished",
            "tags": ["pulp:foo:bar", "pulp:repository:some-repo"],
        }
    )
    assert task.repo_id == "some-repo"
